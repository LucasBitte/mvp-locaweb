"""
=============================================================================================
 Analise de recorrencia operacional — PLAN.md Fase 5.
=============================================================================================

 NAO e modelo de ML — regra de negocio deterministica sobre dw.fct_incidentes,
 no mesmo espirito de dw.ref_meta_sla_anual/etl/ref_meta_sla.py.

 Compara os ultimos 30 dias contra os 30 dias imediatamente anteriores
 (janela movel ancorada no ultimo dia com dado em dw.fct_incidentes), por 4
 granularidades: produto, categoria, produto+categoria, categoria+subcategoria.

 Recorrencia != apenas volume alto: uma entidade com poucos incidentes mas
 presente na maioria dos dias e recorrente; uma entidade com muitos
 incidentes concentrados em 1-2 dias e um pico pontual, nao recorrencia.
 `status_recorrencia` combina volume (delta_pct) com regularidade
 (cobertura_dias_atual_pct).

 Grava em dw.fct_recorrencia_operacional (recarga completa a cada execucao —
 migration 028_dw_fct_recorrencia_operacional.sql).
=============================================================================================
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".git").exists() or (p / "etl").is_dir():
            return p
    return start


PROJECT_ROOT = find_project_root(Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

JANELA_DIAS = 30

# Limiares fixos, documentados aqui (nao e saida de modelo estatistico).
MIN_VOLUME_CLASSIFICAVEL = 5      # abaixo disso, nao da pra falar de padrao com confianca
COBERTURA_RECORRENTE_PCT = 50.0   # >= metade dos dias da janela com >=1 incidente
DELTA_ESTAVEL_PCT = 20.0          # |delta| <= isso => "estavel"
COBERTURA_PICO_MAX_PCT = 30.0     # < isso e concentrado em poucos dias
DELTA_PICO_MIN_PCT = 50.0         # alta variacao concentrada em poucos dias => pico pontual


def _md5(*parts: str) -> str:
    return hashlib.md5("||".join(parts).encode("utf-8")).hexdigest()


def carregar_incidentes(engine) -> tuple[pd.DataFrame, pd.Timestamp]:
    df = pd.read_sql("""
        SELECT dpc.produto, dpc.categoria, dpc.subcategoria, dt.data_abertura
        FROM dw.fct_incidentes f
        JOIN dw.dim_produto_categoria dpc ON f.dim_produto_categoria_sk = dpc.dim_produto_categoria_sk
        JOIN dw.dim_tempo dt ON f.dim_tempo_sk = dt.dim_tempo_sk
    """, engine)
    df["data_abertura"] = pd.to_datetime(df["data_abertura"])
    referencia = df["data_abertura"].max()
    return df, referencia


def classificar(delta_pct: float | None, cobertura_pct: float, volume_atual: int) -> str:
    if volume_atual < MIN_VOLUME_CLASSIFICAVEL:
        return "volume_insuficiente"
    if delta_pct is None:
        # volume_baseline = 0: entidade nova nesta janela, sem base de comparacao.
        return "novo_padrao"
    if cobertura_pct < COBERTURA_PICO_MAX_PCT and delta_pct > DELTA_PICO_MIN_PCT:
        return "pico_pontual"
    if cobertura_pct >= COBERTURA_RECORRENTE_PCT:
        if delta_pct > DELTA_ESTAVEL_PCT:
            return "recorrente_crescente"
        if delta_pct < -DELTA_ESTAVEL_PCT:
            return "recorrente_em_queda"
        return "recorrente_estavel"
    return "sem_padrao_claro"


def calcular_grao(df: pd.DataFrame, referencia: pd.Timestamp, granularidade: str,
                   colunas: list[str]) -> pd.DataFrame:
    fim_atual = referencia
    inicio_atual = referencia - pd.Timedelta(days=JANELA_DIAS - 1)
    fim_baseline = inicio_atual - pd.Timedelta(days=1)
    inicio_baseline = fim_baseline - pd.Timedelta(days=JANELA_DIAS - 1)

    atual = df[(df.data_abertura >= inicio_atual) & (df.data_abertura <= fim_atual)]
    baseline = df[(df.data_abertura >= inicio_baseline) & (df.data_abertura <= fim_baseline)]

    vol_atual = atual.groupby(colunas).size().rename("volume_atual")
    vol_baseline = baseline.groupby(colunas).size().rename("volume_baseline")
    dias_atual = atual.groupby(colunas)["data_abertura"].nunique().rename("dias_com_incidente_atual")

    out = pd.concat([vol_atual, vol_baseline, dias_atual], axis=1).fillna(0).reset_index()
    out["volume_atual"] = out["volume_atual"].astype(int)
    out["volume_baseline"] = out["volume_baseline"].astype(int)
    out["dias_com_incidente_atual"] = out["dias_com_incidente_atual"].astype(int)
    out["delta_pct"] = out.apply(
        lambda r: (100 * (r.volume_atual - r.volume_baseline) / r.volume_baseline)
        if r.volume_baseline > 0 else None, axis=1
    )
    out["cobertura_dias_atual_pct"] = 100 * out["dias_com_incidente_atual"] / JANELA_DIAS
    out["status_recorrencia"] = out.apply(
        lambda r: classificar(r.delta_pct, r.cobertura_dias_atual_pct, r.volume_atual), axis=1
    )

    out["granularidade"] = granularidade
    out["entidade"] = out[colunas].astype(str).agg(" | ".join, axis=1)
    for c in ["produto", "categoria", "subcategoria"]:
        out[c] = out[c] if c in out.columns else None
    out["janela_referencia"] = fim_atual.date()
    return out


def montar_todas_granularidades(df: pd.DataFrame, referencia: pd.Timestamp) -> pd.DataFrame:
    partes = [
        calcular_grao(df, referencia, "produto", ["produto"]),
        calcular_grao(df, referencia, "categoria", ["categoria"]),
        calcular_grao(df, referencia, "produto_categoria", ["produto", "categoria"]),
        calcular_grao(df, referencia, "categoria_subcategoria", ["categoria", "subcategoria"]),
    ]
    return pd.concat(partes, ignore_index=True, sort=False)


def persistir(engine, df: pd.DataFrame) -> None:
    from sqlalchemy import text

    df = df.copy()
    df["data_execucao"] = pd.Timestamp.now()
    df["recorrencia_sk"] = [
        _md5(str(j), g, e) for j, g, e in zip(df["janela_referencia"], df["granularidade"], df["entidade"])
    ]
    cols = ["recorrencia_sk", "janela_referencia", "granularidade", "entidade",
            "produto", "categoria", "subcategoria", "volume_atual", "volume_baseline",
            "delta_pct", "dias_com_incidente_atual", "cobertura_dias_atual_pct",
            "status_recorrencia", "data_execucao"]

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE dw.fct_recorrencia_operacional"))
    df[cols].to_sql("fct_recorrencia_operacional", engine, schema="dw", if_exists="append", index=False)
    print(f"Recorrencia persistida em dw.fct_recorrencia_operacional ({len(df)} linhas, "
          f"janela_referencia={df['janela_referencia'].iloc[0]})")


def main() -> None:
    from etl.db import get_engine

    engine = get_engine()
    incidentes, referencia = carregar_incidentes(engine)
    resultado = montar_todas_granularidades(incidentes, referencia)
    persistir(engine, resultado)

    print("\n== Distribuicao de status por granularidade ==")
    print(resultado.groupby(["granularidade", "status_recorrencia"]).size().unstack(fill_value=0))

    print("\n== Top 10 'recorrente_crescente' (categoria) ==")
    rc = resultado[(resultado.granularidade == "categoria") &
                    (resultado.status_recorrencia == "recorrente_crescente")]
    print(rc.sort_values("delta_pct", ascending=False)
          [["entidade", "volume_atual", "volume_baseline", "delta_pct", "cobertura_dias_atual_pct"]]
          .head(10).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
