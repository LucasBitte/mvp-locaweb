"""
=============================================================================================
 Previsao diaria de volume de incidentes POR PRODUTO — D+1 a D+7 — PLAN.md Fase 4.
=============================================================================================

 Mesma tecnica de ml.fct_previsao_categoria: split proporcional historico
 (share_historico de "produto" sobre ml.ml_base_features) aplicado sobre o
 yhat ja persistido em ml.fct_previsao_diaria_total. NAO e um Prophet por
 corte — mesma ressalva de metodologia ja registrada para categoria/
 prioridade em CLAUDE.md.

 O recorte de regime (`inicio`) usado no share e o mesmo que
 notebooks/forecast_incidentes_revisado.py usaria na mesma execucao (deteccao
 automatica de quebra de patamar via validar_serie()), para ficar consistente
 com shares_categoria/shares_prioridade.

 Requisito de sequenciamento: precisa rodar DEPOIS de
 `python notebooks/forecast_incidentes_revisado.py --fonte sql` (le a origem
 mais recente ja persistida em ml.fct_previsao_diaria_total).

 Grava em ml.fct_previsao_produto (append, idempotente por origem via
 DELETE+INSERT) — migration 027_ml_fct_previsao_produto.sql.
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

from notebooks.forecast_incidentes_revisado import (  # noqa: E402
    _md5,
    calcular_shares,
    carregar_serie,
    validar_serie,
)

MODELO_VERSAO_PRODUTO = "forecast_produto_v1"


def determinar_inicio_regime(serie: pd.DataFrame) -> pd.Timestamp | None:
    """Mesma logica de deteccao de regime do script principal (main()), para o
    share_historico de produto usar o mesmo recorte ja usado por
    shares_categoria/shares_prioridade."""
    ach = validar_serie(serie)
    if ach["quebras_de_patamar_detectadas"]:
        return pd.Timestamp(ach["quebras_de_patamar_detectadas"][0]["data"])
    return None


def carregar_yhat_total(engine) -> pd.DataFrame:
    import sqlalchemy as sa

    df = pd.read_sql(sa.text(
        "SELECT origem, h, horizonte, ds, yhat FROM ml.fct_previsao_diaria_total "
        "WHERE origem = (SELECT MAX(origem) FROM ml.fct_previsao_diaria_total) ORDER BY ds"
    ), engine)
    if df.empty:
        raise RuntimeError(
            "Nenhuma previsao em ml.fct_previsao_diaria_total. Rode "
            "'python notebooks/forecast_incidentes_revisado.py --fonte sql' primeiro."
        )
    return df


def montar_previsao_produto(yhat_total: pd.DataFrame, shares_produto: pd.DataFrame) -> pd.DataFrame:
    base = yhat_total.merge(shares_produto.rename(columns={"valor": "produto"}), how="cross")
    base["yhat_produto"] = base["yhat"] * base["share"]
    base["share_historico"] = base["share"]
    return base


def persistir(engine, df: pd.DataFrame) -> None:
    from sqlalchemy import text

    origem = df["origem"].iloc[0]
    data_execucao = pd.Timestamp.now()
    df = df.copy()
    df["modelo_versao"] = MODELO_VERSAO_PRODUTO
    df["data_execucao"] = data_execucao
    df["previsao_produto_sk"] = [
        _md5(str(o), str(d), str(p)) for o, d, p in zip(df["origem"], df["ds"], df["produto"])
    ]
    cols = ["previsao_produto_sk", "origem", "h", "horizonte", "ds", "produto",
            "share_historico", "yhat_produto", "modelo_versao", "data_execucao"]

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM ml.fct_previsao_produto WHERE origem = :o"), {"o": origem})
    df[cols].to_sql("fct_previsao_produto", engine, schema="ml", if_exists="append", index=False)
    print(f"Previsao persistida em ml.fct_previsao_produto "
          f"(origem={origem}, {df['produto'].nunique()} produtos)")


def main() -> None:
    from etl.db import get_engine

    engine = get_engine()
    serie = carregar_serie("sql")
    inicio = determinar_inicio_regime(serie)

    yhat_total = carregar_yhat_total(engine)
    shares_produto = calcular_shares(engine, "produto", inicio)
    previsao = montar_previsao_produto(yhat_total, shares_produto)
    persistir(engine, previsao)

    print("\n== Top 10 produtos — D+1 ==")
    top = previsao[previsao.h == 1][["produto", "share_historico", "yhat_produto"]]
    print(top.sort_values("yhat_produto", ascending=False).head(10).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
