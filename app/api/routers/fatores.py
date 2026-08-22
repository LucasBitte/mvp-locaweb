"""GET /api/fatores — tela Fatores (PLAN.md Fase 9, docs/prds/etapa5-api.md §4.4).

Regra semântica permanente: Prophet → volume futuro; XGBoost → risco;
SHAP → explicação individual do risco do XGBoost. Nunca misturar as três —
nenhum campo deste payload menciona "previsão"/"amanhã".
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.deps import get_db_engine

router = APIRouter(prefix="/api", tags=["fatores"])

# Heatmap é um painel visual, não uma exportação completa — limitar às N
# categorias de maior volume total evita um heatmap de 141 linhas (todas as
# categorias distintas de dw.dim_produto_categoria) impraticável de exibir.
_TOP_N_HEATMAP_CATEGORIAS = 10


class ImportanciaItem(BaseModel):
    conceito: str | None = None
    feature: str | None = None
    n_colunas: int | None = None
    importance_pct: float
    rank: int


class ShapItem(BaseModel):
    incident_id: str
    feature: str
    shap_value: float
    direcao: Literal["aumenta_risco", "reduz_risco"]
    rank_abs: int
    score_calibrado: float


class HeatmapCelula(BaseModel):
    categoria: str
    dia_semana_num: int
    nome_dia: str
    volume_medio: float


class FatoresResponse(BaseModel):
    importancia_conceitos: list[ImportanciaItem]
    granularidade: Literal["conceito", "coluna"]
    shap_top_risco: list[ShapItem]
    heatmap_categoria_dia: list[HeatmapCelula]


@router.get("/fatores", response_model=FatoresResponse)
def get_fatores(engine: Engine = Depends(get_db_engine)) -> FatoresResponse:
    with engine.connect() as conn:
        data_execucao_conceito = conn.execute(text("SELECT MAX(data_execucao) FROM ml.fct_importancia_conceito")).scalar_one()

        if data_execucao_conceito is not None:
            granularidade = "conceito"
            rows = conn.execute(
                text(
                    """
                    SELECT conceito, n_colunas, importance_pct, rank
                    FROM ml.fct_importancia_conceito
                    WHERE data_execucao = :data_execucao
                    ORDER BY rank
                    """
                ),
                {"data_execucao": data_execucao_conceito},
            ).mappings().all()
            importancia = [
                ImportanciaItem(conceito=r["conceito"], n_colunas=r["n_colunas"], importance_pct=float(r["importance_pct"]), rank=r["rank"])
                for r in rows
            ]
        else:
            granularidade = "coluna"
            data_execucao_feature = conn.execute(text("SELECT MAX(data_execucao) FROM ml.fct_importancia_feature")).scalar_one()
            rows = conn.execute(
                text(
                    """
                    SELECT feature, importance_pct, rank
                    FROM ml.fct_importancia_feature
                    WHERE data_execucao = :data_execucao
                    ORDER BY rank
                    """
                ),
                {"data_execucao": data_execucao_feature},
            ).mappings().all()
            importancia = [
                ImportanciaItem(feature=r["feature"], importance_pct=float(r["importance_pct"]), rank=r["rank"])
                for r in rows
            ]

        # ml.fct_shap_incidente já é populada só com o TOP_N_SHAP (30) de
        # incidentes (grão incidente×feature — ~7 linhas por incidente) — a
        # seleção do top N já aconteceu na origem, não é feita aqui. Um
        # LIMIT por linha aqui truncaria no meio de um incidente (menos de
        # 30 incidentes distintos no resultado); por isso o filtro é só por
        # data_execucao.
        data_execucao_shap = conn.execute(text("SELECT MAX(data_execucao) FROM ml.fct_shap_incidente")).scalar_one()
        shap_rows = conn.execute(
            text(
                """
                SELECT s.incident_id, s.feature, s.shap_value, s.direcao, s.rank_abs, s.score AS score_calibrado
                FROM ml.fct_shap_incidente s
                WHERE s.data_execucao = :data_execucao
                ORDER BY s.score DESC, s.incident_id, s.rank_abs
                """
            ),
            {"data_execucao": data_execucao_shap},
        ).mappings().all()
        shap_top_risco = [
            ShapItem(
                incident_id=r["incident_id"],
                feature=r["feature"],
                shap_value=float(r["shap_value"]),
                direcao=r["direcao"],
                rank_abs=r["rank_abs"],
                score_calibrado=float(r["score_calibrado"]),
            )
            for r in shap_rows
        ]

        heatmap_rows = conn.execute(
            text(
                """
                WITH top_categorias AS (
                    SELECT dpc.categoria, COUNT(*) AS total
                    FROM dw.fct_incidentes fi
                    JOIN dw.dim_produto_categoria dpc ON fi.dim_produto_categoria_sk = dpc.dim_produto_categoria_sk
                    GROUP BY dpc.categoria
                    ORDER BY total DESC
                    LIMIT :top_n
                )
                SELECT dpc.categoria, dt.dia_semana_num, dt.nome_dia,
                       COUNT(*)::float / COUNT(DISTINCT dt.data_abertura) AS volume_medio
                FROM dw.fct_incidentes fi
                JOIN dw.dim_produto_categoria dpc ON fi.dim_produto_categoria_sk = dpc.dim_produto_categoria_sk
                JOIN dw.dim_tempo dt ON fi.dim_tempo_sk = dt.dim_tempo_sk
                WHERE dpc.categoria IN (SELECT categoria FROM top_categorias)
                GROUP BY dpc.categoria, dt.dia_semana_num, dt.nome_dia
                ORDER BY dpc.categoria, dt.dia_semana_num
                """
            ),
            {"top_n": _TOP_N_HEATMAP_CATEGORIAS},
        ).mappings().all()
        heatmap = [
            HeatmapCelula(
                categoria=r["categoria"],
                dia_semana_num=r["dia_semana_num"],
                nome_dia=r["nome_dia"],
                volume_medio=round(float(r["volume_medio"]), 1),
            )
            for r in heatmap_rows
        ]

    return FatoresResponse(
        importancia_conceitos=importancia,
        granularidade=granularidade,
        shap_top_risco=shap_top_risco,
        heatmap_categoria_dia=heatmap,
    )
