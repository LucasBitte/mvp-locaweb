"""
=============================================================================================
 Previsao diaria de volume de incidentes — D+1 a D+7
 Versao revisada do notebook 05_model_forecast_prophet.ipynb
=============================================================================================

 O QUE MUDOU EM RELACAO AO ORIGINAL (as tres alteracoes mais importantes estao comentadas
 em detalhe nos blocos marcados com  [MUDANCA 1] , [MUDANCA 2]  e  [MUDANCA 3] ).

 Este script e auto-contido e executavel. Por padrao le o parquet local; troque
 FONTE = 'sql' para usar o RDS. Nenhum caminho absoluto de Windows e usado.

 Parquets de ingestao centralizados em data/raw/ml/ (raiz do projeto). Artefatos de saida
 (backtest, previsao, diagnostico) vao por padrao para data/ml/, sempre em parquet.

 Requisitos: pandas, numpy, prophet, pyarrow. Toda saida e parquet: nenhuma imagem.
=============================================================================================
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

try:
    from prophet import Prophet  # noqa: E402
except ModuleNotFoundError as e:  # dependencia que nao esta em requirements.txt
    raise SystemExit(
        "prophet nao instalado. Instale com:  pip install prophet\n"
        "(ja consta em requirements-notebooks.txt)"
    ) from e

# ---------------------------------------------------------------------------------------
# Parametros — tudo que era numero fixo no meio do codigo virou parametro nomeado.
# ---------------------------------------------------------------------------------------

COL_DATA = "data_abertura"      # timestamp de abertura do incidente
COL_VOLUME = "total_chamados"   # contador de incidentes por linha (NAO e sempre 1 — ver [MUDANCA 1])
HORIZONTE = 7                   # D+1 .. D+7
MODELO_ARTEFATO = "prophet"     # prefixo dos artefatos: <modelo>_<saida>.parquet
NIVEL_INTERVALO = 0.80          # explicito: o default do Prophet e 0.80, nao 0.95
SEED = 42


@dataclass
class Config:
    """Configuracao do modelo. Cada valor tem justificativa no comentario."""
    # Prophet
    weekly_seasonality: bool = True
    # yearly=False: com menos de um ciclo anual completo de historico, a serie de Fourier
    # anual nao e identificavel — ela absorve mudancas de nivel e extrapola ruido.
    yearly_seasonality: bool = False
    daily_seasonality: bool = False
    seasonality_mode: str = "additive"
    # changepoint_range=1.0: o default 0.8 proibe pontos de mudanca nos ultimos 20% da serie,
    # justamente o trecho que define o nivel de partida de uma previsao de 7 dias.
    changepoint_range: float = 1.0
    changepoint_prior_scale: float = 0.05
    interval_width: float = NIVEL_INTERVALO
    # Sem regressores extras por padrao — ver [MUDANCA 3].
    regressores: list[str] = field(default_factory=list)
    # Se preenchido, o treino usa apenas dados a partir desta data (regime atual).
    inicio_treino: pd.Timestamp | None = None
    feriados: pd.DataFrame | None = None


# =======================================================================================
# 1. CARGA E VALIDACAO DOS DADOS
# =======================================================================================

SQL_AGREGACAO = f"""
    -- ml.ml_forecast_dataset ja tem grao de dia (1 linha = 1 dia, {COL_VOLUME}
    -- ja e a contagem de incidentes daquele dia) -- diferente do antigo
    -- gold_ml.ml_forecast_dataset (grao de incidente, exigia SUM). Sem
    -- agregacao aqui, so leitura direta.
    SELECT {COL_DATA}                  AS ds,
           {COL_VOLUME}                AS y,
           1                           AS n_linhas,
           NULL::timestamp             AS ultimo_evento_do_dia
    FROM ml.ml_forecast_dataset
    ORDER BY 1
"""


def find_project_root(start: Path) -> Path:
    """Sobe a arvore ate achar a raiz do repo (marcada por .git ou etl/)."""
    for p in [start, *start.parents]:
        if (p / ".git").exists() or (p / "etl").is_dir():
            return p
    return start


PROJECT_ROOT = find_project_root(
    Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))  # permite "from etl.db import get_engine"

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"      # fallback de entrada
DATA_IN_DIR = DATA_RAW_DIR / "ml"                 # entrada: parquets de ingestao (gold_ml)
DATA_ML_DIR = PROJECT_ROOT / "data" / "ml"        # saida: artefatos do modelo, em parquet

#: Locais onde o parquet e procurado quando --caminho nao aponta para um arquivo existente.
#: Evita depender do diretorio de onde o script/notebook foi disparado.
#: data/raw/ (centralizado, raiz do projeto) tem prioridade sobre os demais.
LOCAIS_PARQUET = [
    DATA_IN_DIR,
    DATA_RAW_DIR,
    Path.cwd(),
    Path.cwd() / "data" / "raw" / "ml",
    Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd(),
    Path("/mnt/user-data/uploads"),
]


def _resolver_parquet(caminho: str | Path | None) -> Path:
    """Aceita caminho absoluto, relativo ou so o nome do arquivo."""
    nome = Path(caminho or "ml_forecast_dataset.parquet")
    if nome.is_file():
        return nome.resolve()
    for base in LOCAIS_PARQUET:
        cand = base / nome.name
        if cand.is_file():
            return cand.resolve()
    raise FileNotFoundError(
        f"Parquet '{nome}' nao encontrado. Procurei em: "
        + ", ".join(str(b) for b in LOCAIS_PARQUET)
        + ". Passe o caminho completo em --caminho."
    )


def carregar_serie(fonte: str = "parquet", caminho: str | None = None) -> pd.DataFrame:
    """Devolve a serie diaria com uma linha por dia de calendario."""
    if fonte == "sql":
        from etl.db import get_engine
        bruto = pd.read_sql(SQL_AGREGACAO, get_engine())
    else:
        p = _resolver_parquet(caminho)
        raw = pd.read_parquet(p)
        faltando = {COL_DATA, COL_VOLUME} - set(raw.columns)
        if faltando:
            raise KeyError(
                f"Colunas ausentes em {p.name}: {sorted(faltando)}. "
                f"Colunas encontradas: {list(raw.columns)}. "
                f"Ajuste COL_DATA / COL_VOLUME no topo do script."
            )
        # A coluna pode vir como timestamp (grao de incidente) ou ja como date (pre-agregada).
        raw[COL_DATA] = pd.to_datetime(raw[COL_DATA])
        raw["_d"] = raw[COL_DATA].dt.normalize()
        fmt = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
        print(f"[INFO] Parquet: {p}  ({fmt(len(raw))} linhas, "
              f"{fmt(raw['_d'].nunique())} dias distintos)")
        bruto = (raw.groupby("_d")
                    .agg(y=(COL_VOLUME, "sum"),
                         n_linhas=(COL_DATA, "size"),
                         ultimo_evento_do_dia=(COL_DATA, "max"))
                    .reset_index().rename(columns={"_d": "ds"}))
        # Se o parquet ja vier agregado por dia, nao ha hora util para detectar dia parcial.
        if (bruto["n_linhas"] == 1).all():
            print("[INFO] Uma linha por dia no parquet: a checagem de 'ultimo dia parcial' "
                  "nao se aplica e sera ignorada.")
            bruto["ultimo_evento_do_dia"] = pd.NaT

    bruto["ds"] = pd.to_datetime(bruto["ds"])

    # [MUDANCA 1] Reindexacao no calendario completo: dia sem incidente tem de virar
    # linha com y=0, nao linha ausente. Sem isso o Prophet simplesmente ignora o dia e
    # superestima o nivel. Nesta base nao ha lacunas nem zeros, mas o pipeline nao pode
    # depender disso continuar verdadeiro.
    calendario = pd.date_range(bruto.ds.min(), bruto.ds.max(), freq="D")
    serie = (bruto.set_index("ds").reindex(calendario).rename_axis("ds").reset_index())
    serie["y"] = serie["y"].fillna(0).astype(float)
    serie["dow"] = serie.ds.dt.dayofweek
    return serie


def validar_serie(serie: pd.DataFrame, horas_min_ultimo_dia: int = 22) -> dict:
    """Checagens que devem rodar ANTES de qualquer treino. Retorna dict de achados."""
    ach: dict = {}
    ach["n_dias"] = len(serie)
    ach["periodo"] = f"{serie.ds.min().date()} a {serie.ds.max().date()}"
    ach["dias_faltantes_preenchidos_com_zero"] = int(serie["n_linhas"].isna().sum())
    ach["dias_com_zero"] = int((serie.y == 0).sum())
    ach["dias_negativos"] = int((serie.y < 0).sum())
    ach["duplicatas_de_data"] = int(serie.ds.duplicated().sum())

    # Ultimo dia parcial: se o ultimo evento do dia final e muito cedo, a extracao pegou
    # um dia em andamento e o ponto final esta artificialmente baixo.
    ult = serie.iloc[-1]
    if pd.notna(ult.get("ultimo_evento_do_dia")):
        hora = pd.Timestamp(ult["ultimo_evento_do_dia"]).hour
        ach["hora_do_ultimo_evento"] = hora
        ach["ultimo_dia_suspeito_de_ser_parcial"] = bool(hora < horas_min_ultimo_dia)

    # Deteccao de mudanca de patamar: razao entre medianas de 28 dias consecutivos.
    m = serie.y.rolling(28).median()
    razao = (m / m.shift(28)).dropna()
    quebras = razao[(razao > 2) | (razao < 0.5)]
    ach["quebras_de_patamar_detectadas"] = [
        {"data": str(serie.ds.iloc[i].date()), "razao_28d": round(float(r), 2)}
        for i, r in zip(quebras.index, quebras.values)
    ][:10]

    # Sobredispersao: var/media apos remover o nivel movel. ~1 => Poisson; >>1 => nao.
    lvl = serie.y.rolling(28, center=True, min_periods=10).mean()
    ach["razao_variancia_media"] = round(float(((serie.y - lvl) ** 2).mean() / serie.y.mean()), 1)
    return ach


def recorte_regime(serie: pd.DataFrame, inicio: pd.Timestamp | None) -> pd.DataFrame:
    return serie if inicio is None else serie[serie.ds >= inicio].reset_index(drop=True)


# =======================================================================================
# 2. MODELOS — todos com a mesma assinatura: (historico, datas_futuras) -> DataFrame
#    com colunas yhat / yhat_lower / yhat_upper. Isso permite comparar Prophet e
#    baselines dentro do mesmo motor de backtest, sem codigo duplicado.
# =======================================================================================

def prever_prophet(hist: pd.DataFrame, datas_fut: pd.DatetimeIndex, cfg: Config) -> pd.DataFrame:
    treino = recorte_regime(hist, cfg.inicio_treino)
    if len(treino) < 30:
        raise ValueError(f"Historico insuficiente para treinar: {len(treino)} dias.")

    m = Prophet(
        weekly_seasonality=cfg.weekly_seasonality,
        yearly_seasonality=cfg.yearly_seasonality,
        daily_seasonality=cfg.daily_seasonality,
        seasonality_mode=cfg.seasonality_mode,
        changepoint_range=cfg.changepoint_range,
        changepoint_prior_scale=cfg.changepoint_prior_scale,
        interval_width=cfg.interval_width,   # explicito, nunca implicito
        holidays=cfg.feriados,
    )
    for r in cfg.regressores:
        m.add_regressor(r)
    m.fit(treino[["ds", "y"] + cfg.regressores])

    fut = pd.DataFrame({"ds": datas_fut})
    for r in cfg.regressores:
        # Regressor so pode entrar aqui se for CONHECIDO no instante da previsao.
        # Variavel de calendario e conhecida; taxa de violacao de SLA nao e.
        if r == "fim_de_semana":
            fut[r] = (fut.ds.dt.dayofweek >= 5).astype(int)
        else:
            raise ValueError(f"Regressor '{r}' sem regra de projecao futura definida.")

    f = m.predict(fut)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

    # [MUDANCA 2 — parte a] Tratamento explicito de valores negativos.
    # Truncar em zero DEPOIS do ajuste desloca o vies e quebra a leitura do intervalo.
    # Registramos quantas vezes isso aconteceu para que o problema fique visivel; se
    # ocorrer com frequencia, o caminho correto e modelar em escala log1p ou trocar por
    # um modelo de contagem, nao continuar truncando.
    f.attrs["n_yhat_negativos"] = int((f.yhat < 0).sum())
    for c in ["yhat", "yhat_lower", "yhat_upper"]:
        f[c] = f[c].clip(lower=0)
    return f


def _flat(valor: float, datas_fut) -> pd.DataFrame:
    return pd.DataFrame({"ds": datas_fut, "yhat": float(valor),
                         "yhat_lower": np.nan, "yhat_upper": np.nan})


def bl_naive(hist, datas_fut, **_):
    return _flat(hist.y.iloc[-1], datas_fut)


def bl_snaive7(hist, datas_fut, **_):
    ult7 = hist.y.iloc[-7:].values
    return pd.DataFrame({"ds": datas_fut,
                         "yhat": [ult7[(h - 1) % 7] for h in range(1, len(datas_fut) + 1)],
                         "yhat_lower": np.nan, "yhat_upper": np.nan})


def bl_ma(janela: int):
    def f(hist, datas_fut, **_):
        return _flat(hist.y.iloc[-janela:].mean(), datas_fut)
    f.__name__ = f"bl_ma{janela}"
    return f


def bl_media_dow(hist, datas_fut, n_semanas: int = 4, **_):
    h = hist.set_index("ds")
    vals = []
    for d in datas_fut:
        mesmo = h[h.index.dayofweek == d.dayofweek].y
        vals.append(mesmo.iloc[-n_semanas:].median() if len(mesmo) else h.y.iloc[-7:].mean())
    return pd.DataFrame({"ds": datas_fut, "yhat": vals, "yhat_lower": np.nan, "yhat_upper": np.nan})


def bl_ens_ma7_ma28(hist, datas_fut, **_):
    """Media das medias moveis de 7 e 28 dias. Combina resposta rapida a mudanca de nivel
    (7d) com estabilidade (28d). Neste conjunto de dados foi o melhor previsor testado."""
    return _flat(0.5 * hist.y.iloc[-7:].mean() + 0.5 * hist.y.iloc[-28:].mean(), datas_fut)


BASELINES = {
    "naive_ultimo": bl_naive,
    "snaive_lag7": bl_snaive7,
    "ma7": bl_ma(7),
    "ma28": bl_ma(28),
    "mediana_dow_4sem": bl_media_dow,
    "ens_ma7_ma28": bl_ens_ma7_ma28,
}


# =======================================================================================
# 3. BACKTEST DE ORIGEM MOVEL
# =======================================================================================

def backtest(serie: pd.DataFrame, modelos: dict, primeira_origem: pd.Timestamp,
             horizonte: int = HORIZONTE, passo: int = 1) -> pd.DataFrame:
    """
    [MUDANCA 2 — parte b] Substitui o split unico train/test por origem movel.

    Em cada origem T o modelo enxerga EXCLUSIVAMENTE serie[ds <= T] e preve T+1..T+h,
    que e exatamente a informacao disponivel em producao.

    passo=1 (nao multiplo de 7) e deliberado: com cortes espacados em 7 dias, todo D+1
    cairia sempre no mesmo dia da semana e o efeito de horizonte ficaria confundido com
    efeito de calendario.
    """
    ultima_origem = serie.ds.max() - pd.Timedelta(days=horizonte)
    origens = pd.date_range(primeira_origem, ultima_origem, freq=f"{passo}D")
    idx = serie.set_index("ds")

    linhas = []
    for orig in origens:
        hist = serie[serie.ds <= orig]
        datas_fut = pd.date_range(orig + pd.Timedelta(days=1), periods=horizonte)
        real = idx.reindex(datas_fut).y
        # Denominador do MASE: MAE do naive sazonal (lag 7) DENTRO do treino daquela origem.
        base = recorte_regime(hist, None if len(hist) < 60 else hist.ds.iloc[-90])
        den = float(np.abs(base.y.values[7:] - base.y.values[:-7]).mean())

        for nome, fn in modelos.items():
            try:
                f = fn(hist, datas_fut)
            except Exception as e:  # modelo sem historico suficiente nesta origem
                print(f"  [aviso] {nome} falhou em {orig.date()}: {e}")
                continue
            for h, (d, yhat, lo, hi) in enumerate(
                    zip(f.ds, f.yhat, f.yhat_lower, f.yhat_upper), start=1):
                if pd.isna(real.loc[d]):
                    continue
                linhas.append({"origem": orig, "modelo": nome, "h": h, "ds": d,
                               "dow": d.dayofweek, "y": float(real.loc[d]),
                               "yhat": float(yhat), "lo": lo, "hi": hi, "mase_den": den})

    bt = pd.DataFrame(linhas)
    bt["erro"] = bt.yhat - bt.y
    return bt


# =======================================================================================
# 4. METRICAS
# =======================================================================================

def _bloco_metricas(g: pd.DataFrame) -> pd.Series:
    tem_int = g.lo.notna().any()
    return pd.Series({
        "n": len(g),
        "MAE": g.erro.abs().mean(),
        "RMSE": np.sqrt((g.erro ** 2).mean()),
        # WAPE no lugar de MAPE: nao explode com volume baixo e e interpretavel como
        # "erro total em chamados dividido pelo volume total".
        "WAPE%": 100 * g.erro.abs().sum() / g.y.sum(),
        "vies": g.erro.mean(),                       # com sinal: + = superprevisao
        "MASE": g.erro.abs().mean() / g.mase_den.mean(),
        "cobertura%": 100 * ((g.y >= g.lo) & (g.y <= g.hi)).mean() if tem_int else np.nan,
        "amplitude": (g.hi - g.lo).mean() if tem_int else np.nan,
    })


def metricas_gerais(bt: pd.DataFrame) -> pd.DataFrame:
    return bt.groupby("modelo").apply(_bloco_metricas, include_groups=False)


def metricas_por_horizonte(bt: pd.DataFrame, coluna: str = "MAE") -> pd.DataFrame:
    return (bt.groupby(["modelo", "h"]).apply(_bloco_metricas, include_groups=False)[coluna]
              .unstack())


def metricas_por_dow(bt: pd.DataFrame, coluna: str = "MAE") -> pd.DataFrame:
    return (bt.groupby(["modelo", "dow"]).apply(_bloco_metricas, include_groups=False)[coluna]
              .unstack())


def erro_total_semanal(bt: pd.DataFrame) -> pd.DataFrame:
    """Recorte que importa para dimensionar plantao: a soma dos 7 dias, nao cada dia."""
    s = bt.groupby(["modelo", "origem"]).agg(prev=("yhat", "sum"), real=("y", "sum")).reset_index()
    s["erro"] = s.prev - s.real
    return s.groupby("modelo").apply(lambda g: pd.Series({
        "MAE_semana": g.erro.abs().mean(),
        "WAPE_semana%": 100 * g.erro.abs().sum() / g.real.sum(),
        "vies_semana": g.erro.mean()}), include_groups=False)


def calibrar_intervalos(bt_tuning: pd.DataFrame, bt_aval: pd.DataFrame,
                        modelo: str, nivel: float = NIVEL_INTERVALO) -> pd.DataFrame:
    """
    Recalibracao empirica por horizonte. Os intervalos do Prophet ignoram a
    autocorrelacao dos residuos e subcobrem sistematicamente. Aqui o intervalo passa a
    ser  yhat +- quantis empiricos do erro observado no periodo de tuning, por horizonte.
    IMPORTANTE: os quantis vem SO do tuning; aplicar no proprio periodo de avaliacao
    seria a mesma armadilha de calibrar e avaliar no mesmo dado.
    """
    a = (1 - nivel) / 2
    out = []
    for h in range(1, HORIZONTE + 1):
        erro_tun = bt_tuning.query("modelo == @modelo and h == @h").erro
        sub = bt_aval.query("modelo == @modelo and h == @h").copy()
        if erro_tun.empty or sub.empty:
            continue
        lo_adj, hi_adj = erro_tun.quantile(a), erro_tun.quantile(1 - a)
        sub["lo_cal"] = (sub.yhat - hi_adj).clip(lower=0)
        sub["hi_cal"] = sub.yhat - lo_adj
        out.append({
            "h": h,
            "cobertura_prophet%": 100 * ((sub.y >= sub.lo) & (sub.y <= sub.hi)).mean(),
            "amplitude_prophet": (sub.hi - sub.lo).mean(),
            "cobertura_calibrada%": 100 * ((sub.y >= sub.lo_cal) & (sub.y <= sub.hi_cal)).mean(),
            "amplitude_calibrada": (sub.hi_cal - sub.lo_cal).mean(),
        })
    return pd.DataFrame(out)


def acf_residuos(bt: pd.DataFrame, modelo: str, h: int = 1, max_lag: int = 7) -> pd.Series:
    e = bt.query("modelo == @modelo and h == @h").sort_values("ds").erro.values
    return pd.Series({f"lag_{k}": np.corrcoef(e[:-k], e[k:])[0, 1] for k in range(1, max_lag + 1)})


# =======================================================================================
# 5. DADOS DE DIAGNOSTICO
#    Nao geramos imagem: cada painel do antigo grafico vira um parquet com os numeros
#    que o alimentavam. Quem quiser o grafico plota a partir daqui, e o BI le direto.
# =======================================================================================

def dados_diagnostico(serie: pd.DataFrame, bt: pd.DataFrame, modelo: str,
                      destino: Path, prefixo: str = MODELO_ARTEFATO) -> list[Path]:
    """Grava os insumos dos diagnosticos em parquet e devolve os caminhos escritos.

    Real vs previsto e residuos ja estao em <prefixo>_backtest_bruto.parquet (colunas
    ds, h, y, yhat, erro), entao aqui ficam so os agregados que nao dao para derivar
    sem repetir conta: a serie diaria, a ACF dos residuos e o resumo por horizonte.
    """
    d = bt[bt.modelo == modelo]
    escritos = []

    # Painel 1: serie diaria completa
    caminho = destino / f"{prefixo}_serie_diaria.parquet"
    serie[["ds", "y", "dow"]].to_parquet(caminho, index=False)
    escritos.append(caminho)

    # Painel "ACF dos residuos D+1": autocorrelacao por lag
    acf = acf_residuos(bt, modelo)
    caminho = destino / f"{prefixo}_acf_residuos.parquet"
    (pd.DataFrame({"lag": range(1, len(acf) + 1),
                   "autocorrelacao": acf.values,
                   "modelo": modelo, "horizonte": 1})
       .to_parquet(caminho, index=False))
    escritos.append(caminho)

    # Painel "MAE e cobertura por horizonte", mais a distribuicao dos residuos por horizonte
    resumo = (d.groupby("h")
                .apply(lambda g: pd.Series({
                    "n": len(g),
                    "MAE": g.erro.abs().mean(),
                    "RMSE": np.sqrt((g.erro ** 2).mean()),
                    "vies": g.erro.mean(),
                    "erro_p05": g.erro.quantile(0.05),
                    "erro_mediana": g.erro.median(),
                    "erro_p95": g.erro.quantile(0.95),
                    "cobertura%": 100 * ((g.y >= g.lo) & (g.y <= g.hi)).mean(),
                }), include_groups=False)
                .reset_index())
    resumo["nivel_nominal%"] = 100 * NIVEL_INTERVALO
    resumo["modelo"] = modelo
    caminho = destino / f"{prefixo}_diagnostico_por_horizonte.parquet"
    resumo.to_parquet(caminho, index=False)
    escritos.append(caminho)

    return escritos


# =======================================================================================
# 5b. QUEBRA POR PRIORIDADE/CATEGORIA (split proporcional historico) E PERSISTENCIA
#     Decisao explicita do projeto: nao treina um Prophet por corte -- aplica a
#     proporcao historica de cada prioridade/categoria sobre o total previsto.
# =======================================================================================

MODELO_VERSAO_FORECAST = "prophet_regime"


def _md5(*partes: str) -> str:
    return hashlib.md5("|".join(partes).encode("utf-8")).hexdigest()


def calcular_shares(engine, coluna: str, inicio: pd.Timestamp | None) -> pd.DataFrame:
    """Fracao historica do volume por valor de `coluna` (prioridade_num ou categoria),
    no mesmo periodo de referencia usado no treino do Prophet (recorte de regime).
    """
    from sqlalchemy import text

    filtro = 'WHERE data_abertura >= :inicio' if inicio is not None else ""
    sql = f"""
        SELECT {coluna} AS valor, COUNT(*)::numeric / SUM(COUNT(*)) OVER () AS share
        FROM ml.ml_base_features
        {filtro}
        GROUP BY {coluna}
    """
    params = {"inicio": inicio.date()} if inicio is not None else {}
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def persistir_previsao(engine, f: pd.DataFrame, shares_prioridade: pd.DataFrame,
                       shares_categoria: pd.DataFrame) -> None:
    """Grava a previsao total + quebras por prioridade/categoria em ml.fct_previsao_*.

    Append (nao truncate+insert): cada origem e um run novo, mantido para poder
    comparar previsto x realizado depois. Idempotente por origem -- se a mesma
    origem ja tiver sido gravada, apaga essas linhas antes de reinserir.
    """
    from sqlalchemy import text

    origem = f["origem"].iloc[0].date()
    data_execucao = pd.Timestamp.now()

    total = f[["origem", "horizonte", "ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    total["origem"] = total["origem"].dt.date
    total["ds"] = total["ds"].dt.date
    total["h"] = total["horizonte"].str.replace("D+", "", regex=False).astype(int)
    total["modelo_versao"] = MODELO_VERSAO_FORECAST
    total["data_execucao"] = data_execucao
    total["previsao_total_sk"] = [
        _md5(str(o), str(d)) for o, d in zip(total["origem"], total["ds"])
    ]

    base = total[["origem", "h", "horizonte", "ds", "yhat"]]

    prioridade = base.merge(shares_prioridade.rename(columns={"valor": "prioridade_num"}), how="cross")
    prioridade["prioridade_num"] = prioridade["prioridade_num"].astype(int)
    prioridade["yhat_prioridade"] = prioridade["yhat"] * prioridade["share"]
    prioridade["share_historico"] = prioridade["share"]
    prioridade["modelo_versao"] = MODELO_VERSAO_FORECAST
    prioridade["data_execucao"] = data_execucao
    prioridade["previsao_prioridade_sk"] = [
        _md5(str(o), str(d), str(p)) for o, d, p in
        zip(prioridade["origem"], prioridade["ds"], prioridade["prioridade_num"])
    ]

    categoria = base.merge(shares_categoria.rename(columns={"valor": "categoria"}), how="cross")
    categoria["yhat_categoria"] = categoria["yhat"] * categoria["share"]
    categoria["share_historico"] = categoria["share"]
    categoria["modelo_versao"] = MODELO_VERSAO_FORECAST
    categoria["data_execucao"] = data_execucao
    categoria["previsao_categoria_sk"] = [
        _md5(str(o), str(d), str(c)) for o, d, c in
        zip(categoria["origem"], categoria["ds"], categoria["categoria"])
    ]

    cols_total = ["previsao_total_sk", "origem", "h", "horizonte", "ds", "yhat",
                  "yhat_lower", "yhat_upper", "modelo_versao", "data_execucao"]
    cols_prio = ["previsao_prioridade_sk", "origem", "h", "horizonte", "ds", "prioridade_num",
                 "share_historico", "yhat_prioridade", "modelo_versao", "data_execucao"]
    cols_cat = ["previsao_categoria_sk", "origem", "h", "horizonte", "ds", "categoria",
                "share_historico", "yhat_categoria", "modelo_versao", "data_execucao"]

    with engine.begin() as conn:
        for tabela in ["fct_previsao_diaria_total", "fct_previsao_prioridade", "fct_previsao_categoria"]:
            conn.execute(text(f"DELETE FROM ml.{tabela} WHERE origem = :o"), {"o": origem})

    total[cols_total].to_sql("fct_previsao_diaria_total", engine, schema="ml", if_exists="append", index=False)
    prioridade[cols_prio].to_sql("fct_previsao_prioridade", engine, schema="ml", if_exists="append", index=False)
    categoria[cols_cat].to_sql("fct_previsao_categoria", engine, schema="ml", if_exists="append", index=False)
    print(f"✅ Previsao persistida em ml.fct_previsao_* (origem={origem}, "
          f"{len(shares_prioridade)} prioridades, {len(shares_categoria)} categorias)")


# =======================================================================================
# 6. EXECUCAO
# =======================================================================================

def main(argv: list[str] | None = None):
    """argv=None le a linha de comando. Dentro de notebook, passe a lista explicitamente
    ou use executar(...) — o argparse tentaria interpretar o argv do proprio Jupyter."""
    p = argparse.ArgumentParser()
    p.add_argument("--fonte", default="parquet", choices=["parquet", "sql"])
    p.add_argument("--caminho", default="ml_forecast_dataset.parquet")
    p.add_argument("--saida", default=str(DATA_ML_DIR))
    p.add_argument("--inicio-regime", default=None,
                   help="ISO date. Se omitido, usa a quebra detectada automaticamente.")
    p.add_argument("--fim-tuning", default=None,
                   help="ISO date. Origens ate esta data sao tuning; depois, avaliacao final.")
    args = p.parse_args(argv)

    np.random.seed(SEED)
    out = Path(args.saida); out.mkdir(parents=True, exist_ok=True)

    # ---------------- carga e validacao ----------------
    serie = carregar_serie(args.fonte, args.caminho)
    ach = validar_serie(serie)
    print("== VALIDACAO DA SERIE ==")
    print(json.dumps(ach, indent=2, ensure_ascii=False, default=str))
    if ach.get("ultimo_dia_suspeito_de_ser_parcial"):
        print("\n[ALERTA] Ultimo dia possivelmente parcial. Em producao, DESCARTE o ultimo dia\n"
              "         antes de treinar: um ponto artificialmente baixo na origem puxa a\n"
              "         tendencia para baixo exatamente onde a previsao comeca.\n")

    # ---------------- recorte de regime ----------------
    if args.inicio_regime:
        inicio = pd.Timestamp(args.inicio_regime)
    elif ach["quebras_de_patamar_detectadas"]:
        inicio = pd.Timestamp(ach["quebras_de_patamar_detectadas"][0]["data"])
        print(f"[INFO] Quebra de patamar detectada. Treino restrito a partir de {inicio.date()}.")
    else:
        inicio = None

    cfg_regime = Config(inicio_treino=inicio)
    cfg_hist = Config(inicio_treino=None)

    modelos = {
        "prophet_regime": lambda h, f: prever_prophet(h, f, cfg_regime),
        "prophet_hist_completo": lambda h, f: prever_prophet(h, f, cfg_hist),
        **BASELINES,
    }

    # ---------------- backtest ----------------
    # Primeira origem: 45 dias apos o inicio do regime, para haver treino minimo viavel.
    primeira = (inicio + pd.Timedelta(days=45)) if inicio is not None else serie.ds.min() + pd.Timedelta(days=90)
    print(f"\n== BACKTEST DE ORIGEM MOVEL ==\ninitial ~ {(primeira - (inicio or serie.ds.min())).days} dias | "
          f"period = 1 dia | horizon = {HORIZONTE} dias")
    bt = backtest(serie, modelos, primeira_origem=primeira)
    print(f"origens: {bt.origem.nunique()} | previsoes avaliadas: {len(bt)}")

    fim_tuning = pd.Timestamp(args.fim_tuning) if args.fim_tuning else (
        bt.origem.min() + (bt.origem.max() - bt.origem.min()) * 0.55)
    bt["periodo"] = np.where(bt.origem <= fim_tuning, "tuning", "avaliacao_final")
    print(f"tuning ate {fim_tuning.date()} | avaliacao final depois disso "
          f"({bt[bt.periodo=='avaliacao_final'].origem.nunique()} origens)")
    bt.to_parquet(out / f"{MODELO_ARTEFATO}_backtest_bruto.parquet")

    # ---------------- metricas ----------------
    for per in ["tuning", "avaliacao_final"]:
        s = bt[bt.periodo == per]
        print(f"\n{'='*88}\nMETRICAS AGREGADAS — {per}\n{'='*88}")
        print(metricas_gerais(s).round(2).sort_values("MAE").to_string())
        print(f"\nMAE por horizonte — {per}")
        print(metricas_por_horizonte(s).round(0).to_string())

    final = bt[bt.periodo == "avaliacao_final"]
    # Metricas da avaliacao final tambem viram parquet: e o que o BI le, sem reprocessar.
    (metricas_gerais(final).reset_index()
        .to_parquet(out / f"{MODELO_ARTEFATO}_metricas_avaliacao_final.parquet", index=False))
    print(f"\n{'='*88}\nERRO DO TOTAL DA SEMANA (soma D+1..D+7) — avaliacao final\n{'='*88}")
    print(erro_total_semanal(final).round(1).sort_values("MAE_semana").to_string())

    print(f"\nMAE por dia da semana (0=seg) — avaliacao final")
    print(metricas_por_dow(final).round(0).to_string())

    print(f"\nACF dos residuos D+1 (prophet_regime):")
    print(acf_residuos(final, "prophet_regime").round(2).to_string())

    print(f"\n{'='*88}\nCALIBRACAO DOS INTERVALOS (nominal {NIVEL_INTERVALO:.0%})\n{'='*88}")
    print(calibrar_intervalos(bt[bt.periodo == "tuning"], final, "prophet_regime")
          .round(0).to_string(index=False))

    # ---------------- veredito automatico vs baselines ----------------
    g = metricas_gerais(final)["MAE"]
    melhor_bl = g[[k for k in BASELINES if k in g.index]].idxmin()
    print(f"\n{'='*88}\nVEREDITO\n{'='*88}")
    for mdl in ["prophet_regime", "prophet_hist_completo"]:
        if mdl in g.index:
            delta = 100 * (g[mdl] - g[melhor_bl]) / g[melhor_bl]
            veredito = "SUPERA" if delta < -5 else ("EMPATA" if abs(delta) <= 5 else "PERDE PARA")
            print(f"{mdl}: MAE {g[mdl]:.0f} | {veredito} o melhor baseline "
                  f"({melhor_bl}, MAE {g[melhor_bl]:.0f}) por {delta:+.1f}%")

    # ---------------- previsao operacional D+1..D+7 ----------------
    # [MUDANCA 3] A origem da previsao e o ULTIMO DIA COM DADO, nunca datetime.now().
    # No original, future_dates partia de hoje; rodando o notebook meses depois da
    # extracao, o modelo extrapolava centenas de dias alem do treino sem erro nenhum.
    origem = serie.ds.max()
    datas_fut = pd.date_range(origem + pd.Timedelta(days=1), periods=HORIZONTE)
    f = prever_prophet(serie, datas_fut, cfg_regime)
    f.insert(0, "horizonte", [f"D+{i}" for i in range(1, HORIZONTE + 1)])
    f.insert(0, "origem", origem)
    if f.attrs.get("n_yhat_negativos"):
        print(f"\n[ALERTA] {f.attrs['n_yhat_negativos']} previsoes negativas truncadas em zero.")
    print(f"\n{'='*88}\nPREVISAO D+1..D+7 (origem = {origem.date()})\n{'='*88}")
    num = ["yhat", "yhat_lower", "yhat_upper"]
    print(f.assign(**{c: f[c].round(0) for c in num}).to_string(index=False))
    print(f"total previsto para a semana: {f.yhat.sum():.0f} chamados")
    f.to_parquet(out / f"{MODELO_ARTEFATO}_forecast_d1_d7.parquet", index=False)

    if args.fonte == "sql":
        from etl.db import get_engine
        engine_persist = get_engine()
        shares_prioridade = calcular_shares(engine_persist, "prioridade_num", inicio)
        shares_categoria = calcular_shares(engine_persist, "categoria", inicio)
        persistir_previsao(engine_persist, f, shares_prioridade, shares_categoria)

    escritos = dados_diagnostico(serie, final, "prophet_regime", out)
    nomes = ", ".join(c.name for c in escritos)
    print(f"\nArtefatos em: {out.resolve()}  ({MODELO_ARTEFATO}_backtest_bruto.parquet, "
          f"{MODELO_ARTEFATO}_metricas_avaliacao_final.parquet, "
          f"{MODELO_ARTEFATO}_forecast_d1_d7.parquet, {nomes})")


def executar(caminho: str = "ml_forecast_dataset.parquet",
             saida: str = str(DATA_ML_DIR),
             fonte: str = "parquet",
             inicio_regime: str | None = None,
             fim_tuning: str | None = None):
    """
    Entrada para notebook. Equivale a chamar o script pela linha de comando.

        from forecast_incidentes_revisado import executar
        executar()  # le de data/raw/ml/ml_forecast_dataset.parquet, grava em data/ml/

    Para trocar de volta para o RDS:  executar(fonte="sql")
    """
    argv = ["--fonte", fonte, "--caminho", str(caminho), "--saida", str(saida)]
    if inicio_regime:
        argv += ["--inicio-regime", inicio_regime]
    if fim_tuning:
        argv += ["--fim-tuning", fim_tuning]
    return main(argv)


if __name__ == "__main__":
    main()
