"""GET /api/detalhe — tela Detalhe/"Operação" (PLAN.md Fase 7, docs/prds/etapa5-api.md §4.2).

Responde: P2/P3 estão sob risco? Qual categoria/produto lidera o volume
previsto? Onde há recorrência (produto/categoria, não item de configuração).
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.deps import get_db_engine

router = APIRouter(prefix="/api", tags=["detalhe"])

# status_recorrencia que merecem destaque nesta tela/alerta — exclui
# 'volume_insuficiente'/'sem_padrao_claro' (ruído) e 'pico_pontual'/
# 'novo_padrao'/'recorrente_em_queda' (não são o padrão "recorrente e ativo"
# que a tela quer destacar). Enum completo em docs/dicionario-dados.md.
_STATUS_RECORRENCIA_RELEVANTES = ("recorrente_crescente", "recorrente_estavel")
_TOP_N_ENTIDADES = 5
_TOP_N_RECORRENCIA = 10


class PrioridadeDetalhe(BaseModel):
    prioridade_num: int
    bucket_prioridade: str
    previsto: float
    threshold_sla_horas: Optional[int]
    metodologia: str = "proporcao_historica"
    share_historico: float
    pct_limite_mensal: None = None
    is_placeholder_limite: bool = True


class EntidadeDetalhe(BaseModel):
    nome: str
    yhat: float
    share_historico: float
    metodologia: str = "proporcao_historica"


class EntidadeRecorrente(BaseModel):
    entidade: str
    volume_atual: int
    volume_baseline: int
    delta_pct: Optional[float]
    cobertura_dias_atual_pct: float
    status_recorrencia: str


class RecorrenciaBloco(BaseModel):
    granularidade: str
    janela_referencia: str
    entidades: list[EntidadeRecorrente]


class DetalheResponse(BaseModel):
    prioridades: list[PrioridadeDetalhe]
    agrupamento: Literal["categoria", "produto"]
    top_entidades: list[EntidadeDetalhe]
    recorrencia: RecorrenciaBloco


@router.get("/detalhe", response_model=DetalheResponse)
def get_detalhe(
    horizonte: str = Query(default="D+1"),
    agrupamento: Literal["categoria", "produto"] = Query(default="categoria"),
    engine: Engine = Depends(get_db_engine),
) -> DetalheResponse:
    with engine.connect() as conn:
        origem_prio = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_prioridade")).scalar_one()
        prio_rows = conn.execute(
            text(
                """
                SELECT fp.prioridade_num, dp.bucket_prioridade, fp.yhat_prioridade,
                       dp.threshold_sla_horas, fp.share_historico
                FROM ml.fct_previsao_prioridade fp
                JOIN dw.dim_prioridade dp ON fp.prioridade_num = dp.prioridade_num
                WHERE fp.origem = :origem AND fp.horizonte = :horizonte
                ORDER BY fp.prioridade_num
                """
            ),
            {"origem": origem_prio, "horizonte": horizonte},
        ).mappings().all()
        prioridades = [
            PrioridadeDetalhe(
                prioridade_num=r["prioridade_num"],
                bucket_prioridade=r["bucket_prioridade"],
                previsto=round(float(r["yhat_prioridade"]), 1),
                threshold_sla_horas=r["threshold_sla_horas"],
                share_historico=float(r["share_historico"]),
            )
            for r in prio_rows
        ]

        if agrupamento == "categoria":
            origem_ent = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_categoria")).scalar_one()
            ent_rows = conn.execute(
                text(
                    """
                    SELECT categoria AS nome, yhat_categoria AS yhat, share_historico
                    FROM ml.fct_previsao_categoria
                    WHERE origem = :origem AND horizonte = :horizonte
                    ORDER BY yhat_categoria DESC
                    LIMIT :top_n
                    """
                ),
                {"origem": origem_ent, "horizonte": horizonte, "top_n": _TOP_N_ENTIDADES},
            ).mappings().all()
        else:
            origem_ent = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_produto")).scalar_one()
            ent_rows = conn.execute(
                text(
                    """
                    SELECT produto AS nome, yhat_produto AS yhat, share_historico
                    FROM ml.fct_previsao_produto
                    WHERE origem = :origem AND horizonte = :horizonte
                    ORDER BY yhat_produto DESC
                    LIMIT :top_n
                    """
                ),
                {"origem": origem_ent, "horizonte": horizonte, "top_n": _TOP_N_ENTIDADES},
            ).mappings().all()
        top_entidades = [
            EntidadeDetalhe(nome=r["nome"], yhat=round(float(r["yhat"]), 1), share_historico=float(r["share_historico"]))
            for r in ent_rows
        ]

        janela_referencia = conn.execute(text("SELECT MAX(janela_referencia) FROM dw.fct_recorrencia_operacional")).scalar_one()
        rec_rows = conn.execute(
            text(
                """
                SELECT entidade, volume_atual, volume_baseline, delta_pct,
                       cobertura_dias_atual_pct, status_recorrencia
                FROM dw.fct_recorrencia_operacional
                WHERE janela_referencia = :janela
                  AND granularidade = :granularidade
                  AND status_recorrencia = ANY(:status_relevantes)
                ORDER BY delta_pct DESC NULLS LAST
                LIMIT :top_n
                """
            ),
            {
                "janela": janela_referencia,
                "granularidade": agrupamento,
                "status_relevantes": list(_STATUS_RECORRENCIA_RELEVANTES),
                "top_n": _TOP_N_RECORRENCIA,
            },
        ).mappings().all()
        recorrencia = RecorrenciaBloco(
            granularidade=agrupamento,
            janela_referencia=str(janela_referencia),
            entidades=[
                EntidadeRecorrente(
                    entidade=r["entidade"],
                    volume_atual=r["volume_atual"],
                    volume_baseline=r["volume_baseline"],
                    delta_pct=float(r["delta_pct"]) if r["delta_pct"] is not None else None,
                    cobertura_dias_atual_pct=float(r["cobertura_dias_atual_pct"]),
                    status_recorrencia=r["status_recorrencia"],
                )
                for r in rec_rows
            ],
        )

    return DetalheResponse(
        prioridades=prioridades,
        agrupamento=agrupamento,
        top_entidades=top_entidades,
        recorrencia=recorrencia,
    )
