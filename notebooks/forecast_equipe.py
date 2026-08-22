"""
=============================================================================================
 Previsao diaria de volume de incidentes POR EQUIPE (grupo_designado) — D+1 a D+7
 Arquitetura hibrida A/B/C sobre o corte de viabilidade aprovado em
 notebooks/06_forecast_investigacao_equipe.ipynb (media diaria de incidentes/equipe).
=============================================================================================

 Grupo A (media diaria >= 5, Prophet individual): Team14, Team11, Team05, Team09.
 Grupo B (1 <= media diaria < 5, diario primeiro, semanal so se "PERDE PARA" o melhor
          baseline): Team12, Team03, Team17, Team02.
 Grupo C (media diaria < 1, serie inviavel, split proporcional do yhat do total):
          Team10, Team16, Team01, Team15, Team07, Team08, Team04, Team06.

 Reaproveita (por import, sem duplicar) Config/prever_prophet/backtest/validar_serie/
 recorte_regime/metricas_gerais/BASELINES/calcular_shares/_md5 de
 notebooks/forecast_incidentes_revisado.py — mesma metodologia/hiperparametros de base
 do forecast total.

 Requisito de sequenciamento: precisa rodar DEPOIS de
 `python notebooks/forecast_incidentes_revisado.py --fonte sql` na mesma origem (Grupo C
 le o yhat ja persistido em ml.fct_previsao_diaria_total).

 Grava em ml.fct_previsao_grupo (append, idempotente por origem via DELETE+INSERT).
=============================================================================================
"""
from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".git").exists() or (p / "etl").is_dir():
            return p
    return start


PROJECT_ROOT = find_project_root(
    Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notebooks.forecast_incidentes_revisado import (  # noqa: E402
    BASELINES,
    Config,
    _md5,
    backtest,
    calcular_shares,
    metricas_gerais,
    prever_prophet,
    validar_serie,
)

HORIZONTE = 7
NIVEL_INTERVALO = 0.80
SEED = 42
MODELO_VERSAO_GRUPO = "forecast_equipe_v1"

GRUPO_A = ["Team14", "Team11", "Team05", "Team09"]
GRUPO_B = ["Team12", "Team03", "Team17", "Team02"]
GRUPO_C = ["Team10", "Team16", "Team01", "Team15", "Team07", "Team08", "Team04", "Team06"]

# Detector de "storm day": um pai (incidente_pai != 'Independente') respondendo por >=40%
# do volume do dia da equipe, com o dia >=2x a mediana diaria historica da propria equipe.
STORM_PCT_MIN = 0.40
STORM_MEDIANA_MULT = 2.0
STORM_N_PAI_MIN_GRUPO_A = 1     # sem piso extra: Grupo A tem volume suficiente p/ o filtro bastar
STORM_N_PAI_MIN_GRUPO_B_DIARIO = 10  # piso mais estrito p/ equipes de mediana baixa que ficam diarias


# =======================================================================================
# 1. CARGA POR EQUIPE
# =======================================================================================

def carregar_serie_equipe(engine, equipe: str) -> pd.DataFrame:
    """Serie diaria de UMA equipe, calendario completo, zero-fill.

    Nao reaproveita carregar_serie() do script original: aquela funcao le
    ml.ml_forecast_dataset, que ja vem agregado por dia (sem grupo_designado).
    """
    bruto = pd.read_sql(
        "SELECT data_abertura AS ds, COUNT(*) AS y "
        "FROM ml.ml_base_features WHERE grupo_designado = %(equipe)s "
        "GROUP BY 1 ORDER BY 1",
        engine, params={"equipe": equipe},
    )
    bruto["ds"] = pd.to_datetime(bruto["ds"])

    limites = pd.read_sql(
        "SELECT MIN(data_abertura) AS mn, MAX(data_abertura) AS mx FROM ml.ml_base_features",
        engine,
    ).iloc[0]
    calendario = pd.date_range(limites["mn"], limites["mx"], freq="D")
    serie = (bruto.set_index("ds").reindex(calendario).rename_axis("ds").reset_index())
    serie["n_linhas"] = serie["y"]  # NaN nos dias ausentes do bruto -- usado por validar_serie()
    serie["y"] = serie["y"].fillna(0).astype(float)
    serie["dow"] = serie.ds.dt.dayofweek
    return serie


def carregar_incidentes_equipe(engine, equipe: str) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT data_abertura AS ds, incidente_pai FROM ml.ml_base_features "
        "WHERE grupo_designado = %(equipe)s",
        engine, params={"equipe": equipe},
    ).assign(ds=lambda d: pd.to_datetime(d["ds"]))


# =======================================================================================
# 2. DETECTOR DE STORM DAY -> Prophet holidays
# =======================================================================================

def detectar_storm_days(incidentes: pd.DataFrame, serie: pd.DataFrame, n_pai_min: int = 1) -> pd.DataFrame:
    """Dias em que um unico incidente_pai domina o volume da equipe naquele dia.

    Conta so os filhos ABERTOS PARA A MESMA EQUIPE (grupo_designado == equipe) — um
    incidente-pai pode ter outros filhos noutras equipes, isso e irrelevante aqui: o que
    importa e o choque de carga de trabalho desta equipe especifica, nao o raio de
    explosao total do pai.
    """
    mediana = serie["y"].median()
    piores = (
        incidentes[incidentes["incidente_pai"] != "Independente"]
        .groupby(["ds", "incidente_pai"]).size().rename("n_pai").reset_index()
        .sort_values("n_pai", ascending=False)
        .drop_duplicates("ds")
    )
    tot_dia = incidentes.groupby("ds").size().rename("total_dia").reset_index()
    cand = piores.merge(tot_dia, on="ds")
    cand["pct_dia"] = cand["n_pai"] / cand["total_dia"]
    storms = cand[
        (cand["pct_dia"] >= STORM_PCT_MIN)
        & (cand["total_dia"] >= STORM_MEDIANA_MULT * mediana)
        & (cand["n_pai"] >= n_pai_min)
    ].sort_values("total_dia", ascending=False)
    return storms[["ds", "incidente_pai", "n_pai", "total_dia", "pct_dia"]]


def montar_holidays(storm_dates: pd.Series):
    if storm_dates.empty:
        return None
    return pd.DataFrame({
        "holiday": "storm_day",
        "ds": pd.to_datetime(storm_dates.values),
        "lower_window": 0,
        "upper_window": 0,
    })


# =======================================================================================
# 3. VEREDITO DIARIO — reaproveita a logica de comparacao com baseline do script original
# =======================================================================================

def veredito_diario(bt_final: pd.DataFrame, margem_pct: float = 5.0) -> tuple[str, dict]:
    """SUPERA / EMPATA / PERDE PARA o melhor baseline, por MAE, mesma regra do total."""
    g = metricas_gerais(bt_final)["MAE"]
    disponiveis = [k for k in BASELINES if k in g.index]
    if not disponiveis or "prophet_regime" not in g.index:
        return "SEM_BASELINE", {}
    melhor_bl = g[disponiveis].idxmin()
    delta = 100 * (g["prophet_regime"] - g[melhor_bl]) / g[melhor_bl]
    veredito = "SUPERA" if delta < -margem_pct else ("EMPATA" if abs(delta) <= margem_pct else "PERDE PARA")
    return veredito, {"melhor_baseline": melhor_bl, "delta_pct": round(float(delta), 1),
                       "mae_prophet": round(float(g["prophet_regime"]), 2),
                       "mae_baseline": round(float(g[melhor_bl]), 2)}


# =======================================================================================
# 4. PIPELINE DIARIO (Grupo A e tentativa diaria do Grupo B) — 1 equipe por chamada
# =======================================================================================

def rodar_diario(engine, equipe: str, n_pai_min: int) -> dict:
    serie = carregar_serie_equipe(engine, equipe)
    incidentes = carregar_incidentes_equipe(engine, equipe)
    ach = validar_serie(serie)

    storms = detectar_storm_days(incidentes, serie, n_pai_min=n_pai_min)
    feriados = montar_holidays(storms["ds"])

    # RUNWAY_MINIMO_DIAS: o detector de quebra de patamar (validar_serie, herdado do
    # forecast total) compara medianas moveis de 28 dias e pode apontar uma quebra bem
    # perto do fim da serie -- comum em series por equipe, mais curtas/ruidosas que a
    # serie do total. Se nao sobrar runway suficiente para 45 dias de treino minimo +
    # 7 dias de horizonte apos a quebra, o backtest ficaria vazio (bug descoberto ao
    # rodar Team11: quebra apontada no ultimo dia da serie). Nesse caso, ignora a
    # quebra e usa o historico completo -- mais seguro que travar o pipeline.
    RUNWAY_MINIMO_DIAS = 52  # 45 (1a origem) + 7 (horizonte) apos o inicio do regime
    inicio = None
    if ach["quebras_de_patamar_detectadas"]:
        candidato = pd.Timestamp(ach["quebras_de_patamar_detectadas"][0]["data"])
        if candidato <= serie.ds.max() - pd.Timedelta(days=RUNWAY_MINIMO_DIAS):
            inicio = candidato
        else:
            print(f"[AVISO] {equipe}: quebra de patamar detectada em {candidato.date()} "
                  f"nao deixa runway suficiente para backtest (< {RUNWAY_MINIMO_DIAS} dias "
                  "ate o fim da serie) -- ignorada, usando historico completo.")
    cfg = Config(inicio_treino=inicio, feriados=feriados)

    modelos = {"prophet_regime": lambda h, f: prever_prophet(h, f, cfg), **BASELINES}
    primeira = (inicio + pd.Timedelta(days=45)) if inicio is not None else serie.ds.min() + pd.Timedelta(days=90)
    bt = backtest(serie, modelos, primeira_origem=primeira)
    fim_tuning = bt.origem.min() + (bt.origem.max() - bt.origem.min()) * 0.55
    bt["periodo"] = np.where(bt.origem <= fim_tuning, "tuning", "avaliacao_final")
    final = bt[bt.periodo == "avaliacao_final"]

    veredito, detalhe = veredito_diario(final)
    metricas = metricas_gerais(final).round(2)

    origem = serie.ds.max()
    datas_fut = pd.date_range(origem + pd.Timedelta(days=1), periods=HORIZONTE)
    f = prever_prophet(serie, datas_fut, cfg)
    f.insert(0, "horizonte", [f"D+{i}" for i in range(1, HORIZONTE + 1)])
    f.insert(0, "h", range(1, HORIZONTE + 1))
    f.insert(0, "origem", origem)

    return {
        "equipe": equipe, "serie": serie, "storms": storms, "veredito": veredito,
        "veredito_detalhe": detalhe, "metricas": metricas, "forecast": f, "bt_final": final,
        "achados_qualidade": ach,
    }


# =======================================================================================
# 5. FALLBACK SEMANAL (Grupo B, quando o diario "PERDE PARA")
# =======================================================================================

def prever_prophet_semanal(hist_semanal: pd.DataFrame, semanas_fut: pd.DatetimeIndex) -> pd.DataFrame:
    from prophet import Prophet

    m = Prophet(weekly_seasonality=False, yearly_seasonality=False, daily_seasonality=False,
                seasonality_mode="additive", changepoint_range=1.0, changepoint_prior_scale=0.05,
                interval_width=NIVEL_INTERVALO)
    m.fit(hist_semanal[["ds", "y"]])
    fut = pd.DataFrame({"ds": semanas_fut})
    f = m.predict(fut)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    for c in ["yhat", "yhat_lower", "yhat_upper"]:
        f[c] = f[c].clip(lower=0)
    return f


def distribuir_semana_em_dias(previsao_semanal: pd.DataFrame, serie_diaria: pd.DataFrame,
                              datas_fut: pd.DatetimeIndex) -> pd.DataFrame:
    """Distribui cada yhat_semana pelos dias que ela cobre, via share historico de dow."""
    hist = serie_diaria.copy()
    hist["semana"] = hist["ds"] - pd.to_timedelta(hist["ds"].dt.dayofweek, unit="D")
    tot_semana = hist.groupby("semana")["y"].transform("sum")
    hist["share_dow_bruto"] = np.where(tot_semana > 0, hist["y"] / tot_semana, np.nan)
    share_dow = hist.groupby("dow")["share_dow_bruto"].mean()
    share_dow = share_dow / share_dow.sum()  # renormaliza p/ somar 1 entre os 7 dias

    linhas = []
    for d in datas_fut:
        semana_d = d - pd.Timedelta(days=d.dayofweek)
        sem = previsao_semanal[previsao_semanal.ds == semana_d]
        if sem.empty:
            continue
        sh = share_dow.loc[d.dayofweek]
        yhat_sem, lo_sem, hi_sem = sem.iloc[0][["yhat", "yhat_lower", "yhat_upper"]]
        yhat_dia = yhat_sem * sh
        largura_lo = (yhat_sem - lo_sem) * sh
        largura_hi = (hi_sem - yhat_sem) * sh
        linhas.append({"ds": d, "yhat": yhat_dia,
                       "yhat_lower": max(0.0, yhat_dia - largura_lo),
                       "yhat_upper": yhat_dia + largura_hi})
    return pd.DataFrame(linhas)


def rodar_semanal(serie: pd.DataFrame, origem: pd.Timestamp) -> pd.DataFrame:
    hist = serie.copy()
    hist["semana"] = hist["ds"] - pd.to_timedelta(hist["ds"].dt.dayofweek, unit="D")
    semanal = hist.groupby("semana")["y"].agg(["sum", "count"]).reset_index()
    semanal = semanal[semanal["count"] == 7].rename(columns={"semana": "ds", "sum": "y"})[["ds", "y"]]

    datas_fut = pd.date_range(origem + pd.Timedelta(days=1), periods=HORIZONTE)
    semanas_fut = sorted({d - pd.Timedelta(days=d.dayofweek) for d in datas_fut})
    prev_sem = prever_prophet_semanal(semanal, pd.DatetimeIndex(semanas_fut))

    diario = distribuir_semana_em_dias(prev_sem, serie, datas_fut)
    diario.insert(0, "horizonte", [f"D+{i}" for i in range(1, HORIZONTE + 1)])
    diario.insert(0, "h", range(1, HORIZONTE + 1))
    diario.insert(0, "origem", origem)
    return diario


# =======================================================================================
# 6. GRUPO C — split proporcional do yhat do total
# =======================================================================================

def carregar_yhat_total(engine, origem) -> pd.DataFrame:
    from sqlalchemy import text
    df = pd.read_sql(text(
        "SELECT ds, h, horizonte, yhat FROM ml.fct_previsao_diaria_total "
        "WHERE origem = :o ORDER BY ds"
    ), engine, params={"o": origem})
    if df.empty:
        raise RuntimeError(
            f"Nenhuma previsao em ml.fct_previsao_diaria_total para origem={origem}. "
            "Rode 'python notebooks/forecast_incidentes_revisado.py --fonte sql' primeiro "
            "(mesma origem = mesmo ultimo dia de dado)."
        )
    return df


def split_proporcional_grupo(yhat_total: pd.DataFrame, shares: pd.DataFrame, origem) -> pd.DataFrame:
    shares = shares.rename(columns={"valor": "grupo_designado"})
    out = yhat_total.merge(shares, how="cross")
    out["yhat"] = out["yhat"] * out["share"]
    out.insert(0, "origem", origem)
    return out[["origem", "h", "horizonte", "ds", "grupo_designado", "yhat", "share"]]


# =======================================================================================
# 7. PERSISTENCIA
# =======================================================================================

def persistir_previsao_grupo(engine, linhas: pd.DataFrame) -> None:
    from sqlalchemy import text

    origem = linhas["origem"].iloc[0]
    data_execucao = pd.Timestamp.now()
    linhas = linhas.copy()
    linhas["data_execucao"] = data_execucao
    linhas["modelo_versao"] = MODELO_VERSAO_GRUPO
    linhas["previsao_grupo_sk"] = [
        _md5(str(o), str(d), str(sk)) for o, d, sk in
        zip(linhas["origem"], linhas["ds"], linhas["dim_grupo_sk"])
    ]

    cols = ["previsao_grupo_sk", "origem", "h", "horizonte", "ds", "dim_grupo_sk",
            "yhat", "yhat_lower", "yhat_upper", "metodo", "modelo_versao", "data_execucao"]

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM ml.fct_previsao_grupo WHERE origem = :o"), {"o": origem})
    linhas[cols].to_sql("fct_previsao_grupo", engine, schema="ml", if_exists="append", index=False)
    print(f"Previsao persistida em ml.fct_previsao_grupo (origem={origem}, {len(linhas)} linhas)")


# =======================================================================================
# 8. EXECUCAO
# =======================================================================================

def main(argv: list[str] | None = None):
    p = argparse.ArgumentParser()
    p.add_argument("--fonte", default="sql", choices=["sql"])
    args = p.parse_args(argv)
    assert args.fonte == "sql"

    np.random.seed(SEED)
    from etl.db import get_engine
    engine = get_engine()

    dim_grupo = pd.read_sql("SELECT dim_grupo_sk, grupo_designado FROM dw.dim_grupo", engine)

    resultados = {}
    origem_ref = None

    # ---------------- Grupo A ----------------
    print(f"\n{'='*88}\nGRUPO A — Prophet individual\n{'='*88}")
    linhas_a = []
    for equipe in GRUPO_A:
        r = rodar_diario(engine, equipe, n_pai_min=STORM_N_PAI_MIN_GRUPO_A)
        resultados[equipe] = r
        origem_ref = r["forecast"]["origem"].iloc[0]
        print(f"\n-- {equipe} --")
        print(f"storm days detectados: {len(r['storms'])}")
        if len(r["storms"]):
            print(r["storms"].to_string(index=False))
        print(f"veredito vs baseline: {r['veredito']} {r['veredito_detalhe']}")
        print(r["metricas"].to_string())
        f = r["forecast"].copy()
        f["grupo_designado"] = equipe
        f["metodo"] = "prophet_individual"
        linhas_a.append(f[["origem", "h", "horizonte", "ds", "grupo_designado", "yhat",
                            "yhat_lower", "yhat_upper", "metodo"]])

    # ---------------- Grupo B ----------------
    print(f"\n{'='*88}\nGRUPO B — diario primeiro, semanal so se PERDE PARA\n{'='*88}")
    linhas_b = []
    for equipe in GRUPO_B:
        r = rodar_diario(engine, equipe, n_pai_min=STORM_N_PAI_MIN_GRUPO_B_DIARIO)
        print(f"\n-- {equipe} --")
        print(f"veredito diario vs baseline: {r['veredito']} {r['veredito_detalhe']}")
        print(r["metricas"].to_string())

        if r["veredito"] == "PERDE PARA":
            print(f"[DECISAO] {equipe}: diario perde do baseline -> fallback semanal.")
            f = rodar_semanal(r["serie"], r["forecast"]["origem"].iloc[0])
            metodo = "prophet_semanal"
        else:
            print(f"[DECISAO] {equipe}: diario mantido ({r['veredito']}).")
            f = r["forecast"].copy()
            metodo = "prophet_individual"

        f["grupo_designado"] = equipe
        f["metodo"] = metodo
        linhas_b.append(f[["origem", "h", "horizonte", "ds", "grupo_designado", "yhat",
                            "yhat_lower", "yhat_upper", "metodo"]])

    # ---------------- Grupo C ----------------
    print(f"\n{'='*88}\nGRUPO C — split proporcional do total\n{'='*88}")
    yhat_total = carregar_yhat_total(engine, origem_ref.date())
    shares = calcular_shares(engine, "grupo_designado", None)
    shares_c = shares[shares["valor"].isin(GRUPO_C)]
    split_c = split_proporcional_grupo(yhat_total, shares_c, origem_ref.date())
    print(shares_c.to_string(index=False))
    linha_c = split_c.copy()
    linha_c["yhat_lower"] = np.nan
    linha_c["yhat_upper"] = np.nan
    linha_c["metodo"] = "split_proporcional"
    linhas_c = linha_c[["origem", "h", "horizonte", "ds", "grupo_designado", "yhat",
                        "yhat_lower", "yhat_upper", "metodo"]]

    # ---------------- consolida + persiste ----------------
    todas = pd.concat(linhas_a + linhas_b + [linhas_c], ignore_index=True)
    # Grupo A/B trazem ds/origem como pd.Timestamp (prever_prophet); Grupo C trai como
    # datetime.date (leitura de coluna DATE via pandas/sqlalchemy) -- normaliza os dois
    # lados para Timestamp antes de qualquer groupby/merge por essas colunas.
    todas["ds"] = pd.to_datetime(todas["ds"])
    todas["origem"] = pd.to_datetime(todas["origem"])
    todas = todas.merge(dim_grupo, on="grupo_designado", how="left")
    if todas["dim_grupo_sk"].isna().any():
        faltando = todas.loc[todas["dim_grupo_sk"].isna(), "grupo_designado"].unique()
        raise RuntimeError(f"grupo_designado sem dim_grupo_sk em dw.dim_grupo: {faltando}")

    persistir_previsao_grupo(engine, todas)

    # ---------------- validacao: soma por equipe vs total ----------------
    print(f"\n{'='*88}\nCHECAGEM — soma das equipes vs. ml.fct_previsao_diaria_total\n{'='*88}")
    yhat_total["ds"] = pd.to_datetime(yhat_total["ds"])
    soma_equipes = todas.groupby("ds")["yhat"].sum().reset_index().rename(columns={"yhat": "soma_equipes"})
    comp = soma_equipes.merge(yhat_total[["ds", "yhat"]].rename(columns={"yhat": "yhat_total"}), on="ds")
    comp["diff_pct"] = 100 * (comp["soma_equipes"] - comp["yhat_total"]) / comp["yhat_total"]
    print(comp.round(1).to_string(index=False))
    print("\nNota: divergencia esperada (Grupo A/B usam modelos independentes, nao sao split "
          "do total) — so investigar se a soma dobrar ou cair pela metade.")

    engine.dispose()
    return todas


if __name__ == "__main__":
    main()
