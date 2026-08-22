"""GET /api/kpi — tela KPI/"OLA & Metas" (PLAN.md Fase 8, docs/prds/etapa5-api.md §4.3).

`dw.ref_meta_sla_anual` é dado real (24 linhas, faixas por
prioridade×indicador — só P2/P3). Nunca associar métricas de avaliação de
modelo (ROC-AUC, PR-AUC, Brier, silhouette) a esta tela — KPI é sempre sobre
metas/faixas oficiais (`PLAN.md`, Anexo A, "Correção conceitual importante").
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.deps import get_db_engine
from etl.ref_meta_sla import faixa_meta_sla

router = APIRouter(prefix="/api", tags=["kpi"])

_PRIORIDADES_COM_META = (2, 3)
_INDICADORES = ("ola_quebrado", "volume_tratado")
_ORDEM_FAIXA_META_100PCT = 3  # pct_atingimento=100, ver db/migrations/024_dw_ref_meta_sla_anual.sql


class Faixa(BaseModel):
    faixa_min: Optional[int]
    faixa_max: Optional[int]
    pct_atingimento: float
    ordem_faixa: int


class IndicadorKpi(BaseModel):
    prioridade_num: int
    bucket_prioridade: str
    indicador: Literal["ola_quebrado", "volume_tratado"]
    contagem_acumulada_ano: int
    faixa: Faixa
    faixas: list[Faixa]
    status: Literal["dentro_da_meta", "atencao", "critico"]
    probabilidade_atingir_meta_pct: float
    metodologia_probabilidade: str = "projecao_linear"


class KpiResponse(BaseModel):
    ano: int
    dias_decorridos: int
    dias_restantes: int
    indicadores: list[IndicadorKpi]


def _status_de_pct_atingimento(pct_atingimento: float) -> str:
    if pct_atingimento >= 100:
        return "dentro_da_meta"
    if pct_atingimento >= 50:
        return "atencao"
    return "critico"


def _dias_do_ano(ano: int) -> int:
    return 366 if calendar.isleap(ano) else 365


@router.get("/kpi", response_model=KpiResponse)
def get_kpi(
    ano: Optional[int] = Query(default=None, description="default: ano da âncora temporal do pipeline (PLAN.md Fase 1)"),
    engine: Engine = Depends(get_db_engine),
) -> KpiResponse:
    with engine.connect() as conn:
        ancora: date = conn.execute(text("SELECT MAX(aberto_at) FROM dw.fct_incidentes")).scalar_one()
        ano_ancora = ancora.year
        if ano is None:
            ano = ano_ancora

        dias_totais_do_ano = _dias_do_ano(ano)
        if ano == ano_ancora:
            dias_decorridos = ancora.timetuple().tm_yday
        else:
            # ano diferente da âncora: tratado como ano-calendário completo
            # já encerrado (sem noção de "hoje" fora da âncora do pipeline).
            dias_decorridos = dias_totais_do_ano
        dias_restantes = dias_totais_do_ano - dias_decorridos

        indicadores: list[IndicadorKpi] = []
        for prioridade_num in _PRIORIDADES_COM_META:
            bucket_prioridade = conn.execute(
                text("SELECT bucket_prioridade FROM dw.dim_prioridade WHERE prioridade_num = :p"),
                {"p": prioridade_num},
            ).scalar_one()
            for indicador in _INDICADORES:
                if indicador == "ola_quebrado":
                    contagem = conn.execute(
                        text(
                            """
                            SELECT COUNT(*) FROM dw.fct_incidentes fi
                            JOIN dw.dim_prioridade dp ON fi.dim_prioridade_sk = dp.dim_prioridade_sk
                            JOIN dw.dim_tempo dt ON fi.dim_tempo_sk = dt.dim_tempo_sk
                            WHERE dp.prioridade_num = :p AND dt.ano = :ano AND fi.kpi_status_int = 1
                            """
                        ),
                        {"p": prioridade_num, "ano": ano},
                    ).scalar_one()
                else:
                    contagem = conn.execute(
                        text(
                            """
                            SELECT COUNT(*) FROM dw.fct_incidentes fi
                            JOIN dw.dim_prioridade dp ON fi.dim_prioridade_sk = dp.dim_prioridade_sk
                            JOIN dw.dim_tempo dt ON fi.dim_tempo_sk = dt.dim_tempo_sk
                            WHERE dp.prioridade_num = :p AND dt.ano = :ano
                            """
                        ),
                        {"p": prioridade_num, "ano": ano},
                    ).scalar_one()

                faixa_dict = faixa_meta_sla(engine, prioridade_num, indicador, contagem)
                faixa = Faixa(
                    faixa_min=faixa_dict["faixa_min"],
                    faixa_max=faixa_dict["faixa_max"],
                    pct_atingimento=float(faixa_dict["pct_atingimento"]),
                    ordem_faixa=faixa_dict["ordem_faixa"],
                )

                # As 6 faixas da combinação (prioridade, indicador) — o frontend
                # (tela KPI) precisa delas todas para desenhar a grade de faixas
                # completa, não só a que bateu com a contagem atual.
                faixas_rows = conn.execute(
                    text(
                        """
                        SELECT faixa_min, faixa_max, pct_atingimento, ordem_faixa
                        FROM dw.ref_meta_sla_anual
                        WHERE prioridade_num = :p AND indicador = :ind
                        ORDER BY ordem_faixa
                        """
                    ),
                    {"p": prioridade_num, "ind": indicador},
                ).mappings().all()
                faixas = [
                    Faixa(
                        faixa_min=r["faixa_min"],
                        faixa_max=r["faixa_max"],
                        pct_atingimento=float(r["pct_atingimento"]),
                        ordem_faixa=r["ordem_faixa"],
                    )
                    for r in faixas_rows
                ]

                meta_referencia = conn.execute(
                    text(
                        """
                        SELECT faixa_max FROM dw.ref_meta_sla_anual
                        WHERE prioridade_num = :p AND indicador = :ind AND ordem_faixa = :ordem
                        """
                    ),
                    {"p": prioridade_num, "ind": indicador, "ordem": _ORDEM_FAIXA_META_100PCT},
                ).scalar_one()

                projecao_final = (contagem / dias_decorridos) * dias_totais_do_ano if dias_decorridos > 0 else contagem
                if projecao_final > 0:
                    probabilidade = min(100.0, (float(meta_referencia) / projecao_final) * 100)
                else:
                    probabilidade = 100.0

                indicadores.append(
                    IndicadorKpi(
                        prioridade_num=prioridade_num,
                        bucket_prioridade=bucket_prioridade,
                        indicador=indicador,
                        contagem_acumulada_ano=contagem,
                        faixa=faixa,
                        faixas=faixas,
                        status=_status_de_pct_atingimento(faixa.pct_atingimento),
                        probabilidade_atingir_meta_pct=round(probabilidade, 1),
                    )
                )

    return KpiResponse(
        ano=ano,
        dias_decorridos=dias_decorridos,
        dias_restantes=dias_restantes,
        indicadores=indicadores,
    )
