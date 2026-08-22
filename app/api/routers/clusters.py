"""GET /api/clusters — tela Clusters/"Perfis Operacionais" (PLAN.md Fase 10,
docs/prds/etapa5-api.md §4.5).

**Achado de auditoria (2026-08-22)**: `ml.fct_perfil_cluster.taxa_sla_violado_pct`
é calculada em `notebooks/model_clustering_kmeans_Revisado.ipynb` a partir de
`excedeu_tempo_esperado` (duração > threshold da prioridade, ~95% do total),
**não** do indicador oficial de SLA (`dw.fct_incidentes.kpi_status_int=1`,
~0,95% do total — o mesmo usado na tela KPI). São duas definições diferentes
de "violação" com uma ordem de grandeza de distância; expor o nome
`taxa_sla_violado_pct` sem qualificação contradiria a tela KPI. Decisão
(checkpoint humano, não retreino): renomear o campo para
`taxa_excedeu_tempo_esperado_pct` e documentar a diferença diretamente no
payload (`nota_metrica_sla`) — sem alterar `ml.fct_perfil_cluster` nem
retreinar o K-Means.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.deps import get_db_engine

router = APIRouter(prefix="/api", tags=["clusters"])

_NOTA_METRICA_SLA = (
    "taxa_excedeu_tempo_esperado_pct mede duração > threshold da prioridade "
    "(heurística usada como rótulo de treino do XGBoost) — não é o indicador "
    "oficial de SLA (kpi_status_int, exibido na tela KPI), que é ordens de "
    "grandeza menor no mesmo banco."
)


class ClusterItem(BaseModel):
    cluster_id: str
    nome_perfil: str
    descricao_curta: str
    tags: list[str]
    cor_hex: str
    n_incidentes: int
    pct_volume: float
    duracao_media_horas: float | None
    taxa_resolucao_pct: float | None
    taxa_excedeu_tempo_esperado_pct: float | None


class ClustersResponse(BaseModel):
    clusters: list[ClusterItem]
    modelo_versao: str
    data_execucao: str
    nota_metrica_sla: str = _NOTA_METRICA_SLA


@router.get("/clusters", response_model=ClustersResponse)
def get_clusters(engine: Engine = Depends(get_db_engine)) -> ClustersResponse:
    with engine.connect() as conn:
        data_execucao = conn.execute(text("SELECT MAX(data_execucao) FROM ml.fct_perfil_cluster")).scalar_one()
        rows = conn.execute(
            text(
                """
                SELECT d.cluster_id, d.nome_perfil, d.descricao_curta, d.tags, d.cor_hex,
                       p.modelo_versao, p.n_incidentes, p.pct_volume, p.duracao_media_horas,
                       p.taxa_resolucao_pct, p.taxa_sla_violado_pct
                FROM ml.dim_cluster d
                JOIN ml.fct_perfil_cluster p ON d.cluster_id = p.cluster_id
                WHERE p.data_execucao = :data_execucao
                ORDER BY d.cluster_id
                """
            ),
            {"data_execucao": data_execucao},
        ).mappings().all()

        modelo_versao = rows[0]["modelo_versao"] if rows else ""
        clusters = [
            ClusterItem(
                cluster_id=r["cluster_id"],
                nome_perfil=r["nome_perfil"],
                descricao_curta=r["descricao_curta"],
                tags=[t.strip() for t in r["tags"].split(",")],
                cor_hex=r["cor_hex"],
                n_incidentes=r["n_incidentes"],
                pct_volume=float(r["pct_volume"]),
                duracao_media_horas=float(r["duracao_media_horas"]) if r["duracao_media_horas"] is not None else None,
                taxa_resolucao_pct=float(r["taxa_resolucao_pct"]) if r["taxa_resolucao_pct"] is not None else None,
                taxa_excedeu_tempo_esperado_pct=float(r["taxa_sla_violado_pct"]) if r["taxa_sla_violado_pct"] is not None else None,
            )
            for r in rows
        ]

    return ClustersResponse(
        clusters=clusters,
        modelo_versao=modelo_versao,
        data_execucao=str(data_execucao),
    )
