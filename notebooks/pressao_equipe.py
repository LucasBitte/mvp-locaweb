"""
=============================================================================================
 Pressao Operacional Prevista por equipe — PLAN.md Fase 3.
=============================================================================================

 Compara o forecast D+1..D+7 de ml.fct_previsao_grupo contra a media
 historica diaria da propria equipe (calendario completo 2025, zero-fill,
 mesma serie usada em notebooks/forecast_equipe.py).

 pressao_relativa_pct = ((yhat_previsto - media_historica_diaria) / media_historica_diaria) * 100

 NUNCA e capacidade real, headcount ou saturacao contratual — e uma
 comparacao de volume previsto contra o proprio historico da equipe.

 Requisito de sequenciamento: precisa rodar DEPOIS de
 `python notebooks/forecast_equipe.py --fonte sql` (le a origem mais recente
 ja persistida em ml.fct_previsao_grupo).

 Grava em ml.fct_pressao_equipe (append, idempotente por origem via
 DELETE+INSERT) — migration 026_ml_fct_pressao_equipe.sql.
=============================================================================================
"""
from __future__ import annotations

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

from notebooks.forecast_equipe import GRUPO_A, GRUPO_B, GRUPO_C, carregar_serie_equipe  # noqa: E402
from notebooks.forecast_incidentes_revisado import _md5  # noqa: E402

MODELO_VERSAO_PRESSAO = "pressao_equipe_v1"

# Faixas fixas, documentadas aqui (nao e saida de modelo estatistico).
# Nota: para equipes de Grupo C (media diaria < 1 incidente/dia), o % e mais
# ruidoso por construcao (denominador pequeno) — ver docs/forecast-por-equipe.md.
LIMIAR_ATENCAO_PCT = 10.0
LIMIAR_CRITICO_PCT = 30.0


def classificar_nivel(pct: float) -> str:
    if pct > LIMIAR_CRITICO_PCT:
        return "critico"
    if pct > LIMIAR_ATENCAO_PCT:
        return "atencao"
    return "normal"


def calcular_medias_historicas(engine) -> dict[str, float]:
    equipes = GRUPO_A + GRUPO_B + GRUPO_C
    return {eq: carregar_serie_equipe(engine, eq)["y"].mean() for eq in equipes}


def montar_pressao(engine, medias: dict[str, float]) -> pd.DataFrame:
    import sqlalchemy as sa

    prev = pd.read_sql(sa.text("""
        SELECT p.origem, p.h, p.horizonte, p.ds, p.dim_grupo_sk,
               g.grupo_designado, p.yhat, p.metodo
        FROM ml.fct_previsao_grupo p
        JOIN dw.dim_grupo g ON p.dim_grupo_sk = g.dim_grupo_sk
        WHERE p.origem = (SELECT MAX(origem) FROM ml.fct_previsao_grupo)
        ORDER BY g.grupo_designado, p.h
    """), engine)
    if prev.empty:
        raise RuntimeError(
            "Nenhuma previsao em ml.fct_previsao_grupo. Rode "
            "'python notebooks/forecast_equipe.py --fonte sql' primeiro."
        )

    prev["media_historica_diaria"] = prev["grupo_designado"].map(medias)
    prev["pressao_relativa_pct"] = (
        100 * (prev["yhat"] - prev["media_historica_diaria"]) / prev["media_historica_diaria"]
    )
    prev["nivel_pressao"] = prev["pressao_relativa_pct"].apply(classificar_nivel)
    return prev


def persistir(engine, df: pd.DataFrame) -> None:
    from sqlalchemy import text

    origem = df["origem"].iloc[0]
    data_execucao = pd.Timestamp.now()
    df = df.copy()
    df["modelo_versao"] = MODELO_VERSAO_PRESSAO
    df["data_execucao"] = data_execucao
    df["metodo_origem"] = df["metodo"]
    df["yhat_previsto"] = df["yhat"]
    df["pressao_equipe_sk"] = [
        _md5(str(o), str(d), str(sk)) for o, d, sk in
        zip(df["origem"], df["ds"], df["dim_grupo_sk"])
    ]

    cols = ["pressao_equipe_sk", "origem", "h", "horizonte", "ds", "dim_grupo_sk",
            "yhat_previsto", "media_historica_diaria", "pressao_relativa_pct",
            "nivel_pressao", "metodo_origem", "modelo_versao", "data_execucao"]

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM ml.fct_pressao_equipe WHERE origem = :o"), {"o": origem})
    df[cols].to_sql("fct_pressao_equipe", engine, schema="ml", if_exists="append", index=False)
    print(f"Pressao persistida em ml.fct_pressao_equipe (origem={origem}, {len(df)} linhas)")


def main() -> None:
    from etl.db import get_engine

    engine = get_engine()
    medias = calcular_medias_historicas(engine)
    pressao = montar_pressao(engine, medias)
    persistir(engine, pressao)

    print("\n== Resumo D+1 por equipe ==")
    resumo = pressao[pressao.h == 1][
        ["grupo_designado", "yhat", "media_historica_diaria",
         "pressao_relativa_pct", "nivel_pressao", "metodo"]
    ].sort_values("pressao_relativa_pct", ascending=False)
    print(resumo.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
