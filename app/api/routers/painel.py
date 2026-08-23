"""GET /api/painel — tela Painel (PLAN.md Fase 6, docs/prds/etapa5-api.md §4.1).

Responde: quanto teremos em D+1/D+7? Há pico vs. média histórica? Qual o
risco de OLA? Qual equipe está sob maior pressão?
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.deps import get_db_engine

router = APIRouter(prefix="/api", tags=["painel"])

# Faixas fixas de ml.ml_forecast_dataset.pct_violacao_sla (percentual 0-100,
# tipicamente baixo — mediana histórica = 0%). Limiares escolhidos sobre a
# distribuição real (p50=0, p75=1.11, p90=1.85, p95=2.55, max=10) — não é
# achismo de UI, mas também não é uma meta contratual; revisar se a
# distribuição mudar muito entre execuções.
_RISCO_OLA_BAIXO_MAX = 1.0
_RISCO_OLA_MEDIO_MAX = 2.5

# nivel_pressao já vem calculado em ml.fct_pressao_equipe — a API só lê.


class PrevisaoPonto(BaseModel):
    valor: float
    data: str
    modelo_versao: str
    metodologia: Optional[str] = None
    share_historico: Optional[float] = None


class PrevisaoMedia(BaseModel):
    valor: float
    variacao_pct_vs_media_historica: float


class RiscoOla(BaseModel):
    nivel: Literal["baixo", "medio", "alto"]
    pct_violacao_media_movel: float
    janela_dias: int


class SeriePonto(BaseModel):
    data: str
    tipo: Literal["historico", "previsao"]
    valor: float
    horizonte: Optional[str] = None
    metodologia: Optional[str] = None
    share_historico: Optional[float] = None


class PressaoEquipe(BaseModel):
    dim_grupo_sk: str
    grupo_designado: str
    yhat_previsto: float
    media_historica_diaria: float
    pressao_relativa_pct: float
    nivel_pressao: Literal["normal", "atencao", "critico"]
    metodo_origem: str


class PainelResponse(BaseModel):
    previsao_d1: PrevisaoPonto
    previsao_d7_media: PrevisaoMedia
    risco_ola: RiscoOla
    serie: list[SeriePonto]
    pressao_equipes: list[PressaoEquipe]
    metodologia: Optional[str] = None


def _nivel_risco_ola(pct: float) -> str:
    if pct <= _RISCO_OLA_BAIXO_MAX:
        return "baixo"
    if pct <= _RISCO_OLA_MEDIO_MAX:
        return "medio"
    return "alto"


@router.get("/painel", response_model=PainelResponse)
def get_painel(
    prioridade: Optional[int] = Query(default=None, ge=1, le=5, description="1-5; omitido = todas"),
    dias: int = Query(default=30, ge=1, le=365, description="janela do histórico exibido no gráfico"),
    engine: Engine = Depends(get_db_engine),
) -> PainelResponse:
    with engine.connect() as conn:
        if prioridade is None:
            origem = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_diaria_total")).scalar_one()
            previsoes = conn.execute(
                text(
                    """
                    SELECT h, horizonte, ds, yhat, modelo_versao
                    FROM ml.fct_previsao_diaria_total
                    WHERE origem = :origem
                    ORDER BY h
                    """
                ),
                {"origem": origem},
            ).mappings().all()
            media_historica = float(conn.execute(text("SELECT AVG(total_chamados) FROM ml.ml_forecast_dataset")).scalar_one())
            d1 = previsoes[0]
            previsao_d1 = PrevisaoPonto(valor=round(float(d1["yhat"])), data=str(d1["ds"]), modelo_versao=d1["modelo_versao"])
            serie_previsao = [
                SeriePonto(data=str(p["ds"]), tipo="previsao", horizonte=p["horizonte"], valor=round(float(p["yhat"]), 1))
                for p in previsoes
            ]
            metodologia_topo = None
        else:
            origem = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_prioridade")).scalar_one()
            previsoes = conn.execute(
                text(
                    """
                    SELECT h, horizonte, ds, yhat_prioridade, share_historico, modelo_versao
                    FROM ml.fct_previsao_prioridade
                    WHERE origem = :origem AND prioridade_num = :prioridade
                    ORDER BY h
                    """
                ),
                {"origem": origem, "prioridade": prioridade},
            ).mappings().all()
            n_dias_historico = conn.execute(text("SELECT COUNT(*) FROM ml.ml_forecast_dataset")).scalar_one()
            total_historico_prioridade = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM dw.fct_incidentes fi
                    JOIN dw.dim_prioridade dp ON fi.dim_prioridade_sk = dp.dim_prioridade_sk
                    WHERE dp.prioridade_num = :prioridade
                    """
                ),
                {"prioridade": prioridade},
            ).scalar_one()
            media_historica = total_historico_prioridade / n_dias_historico
            d1 = previsoes[0]
            previsao_d1 = PrevisaoPonto(
                valor=round(float(d1["yhat_prioridade"])),
                data=str(d1["ds"]),
                modelo_versao=d1["modelo_versao"],
                metodologia="proporcao_historica",
                share_historico=float(d1["share_historico"]),
            )
            serie_previsao = [
                SeriePonto(
                    data=str(p["ds"]),
                    tipo="previsao",
                    horizonte=p["horizonte"],
                    valor=round(float(p["yhat_prioridade"]), 1),
                    metodologia="proporcao_historica",
                    share_historico=float(p["share_historico"]),
                )
                for p in previsoes
            ]
            metodologia_topo = "proporcao_historica"

        media_d7 = sum(float(p["yhat" if prioridade is None else "yhat_prioridade"]) for p in previsoes) / len(previsoes)
        previsao_d7_media = PrevisaoMedia(
            valor=round(media_d7),
            variacao_pct_vs_media_historica=round(((media_d7 - media_historica) / media_historica) * 100, 1),
        )

        historico_rows = conn.execute(
            text(
                """
                SELECT data_abertura, total_chamados
                FROM ml.ml_forecast_dataset
                ORDER BY data_abertura DESC
                LIMIT :dias
                """
            ),
            {"dias": dias},
        ).mappings().all()
        serie_historico = [
            SeriePonto(data=str(r["data_abertura"]), tipo="historico", valor=float(r["total_chamados"]))
            for r in reversed(historico_rows)
        ]

        janela_dias = 14
        pct_violacao_media_movel = conn.execute(
            text(
                """
                SELECT AVG(pct_violacao_sla) FROM (
                    SELECT pct_violacao_sla FROM ml.ml_forecast_dataset
                    ORDER BY data_abertura DESC LIMIT :janela
                ) recente
                """
            ),
            {"janela": janela_dias},
        ).scalar_one()
        pct_violacao_media_movel = float(pct_violacao_media_movel)
        risco_ola = RiscoOla(
            nivel=_nivel_risco_ola(pct_violacao_media_movel),
            pct_violacao_media_movel=round(pct_violacao_media_movel, 2),
            janela_dias=janela_dias,
        )

        origem_pressao = conn.execute(text("SELECT MAX(origem) FROM ml.fct_pressao_equipe")).scalar_one()
        pressao_rows = conn.execute(
            text(
                """
                SELECT pe.dim_grupo_sk, dg.grupo_designado, pe.yhat_previsto, pe.media_historica_diaria,
                       pe.pressao_relativa_pct, pe.nivel_pressao, pe.metodo_origem
                FROM ml.fct_pressao_equipe pe
                JOIN dw.dim_grupo dg ON pe.dim_grupo_sk = dg.dim_grupo_sk
                WHERE pe.origem = :origem AND pe.h = 1
                ORDER BY pe.pressao_relativa_pct DESC
                """
            ),
            {"origem": origem_pressao},
        ).mappings().all()
        pressao_equipes = [
            PressaoEquipe(
                dim_grupo_sk=r["dim_grupo_sk"],
                grupo_designado=r["grupo_designado"],
                yhat_previsto=float(r["yhat_previsto"]),
                media_historica_diaria=float(r["media_historica_diaria"]),
                pressao_relativa_pct=float(r["pressao_relativa_pct"]),
                nivel_pressao=r["nivel_pressao"],
                metodo_origem=r["metodo_origem"],
            )
            for r in pressao_rows
        ]

    return PainelResponse(
        previsao_d1=previsao_d1,
        previsao_d7_media=previsao_d7_media,
        risco_ola=risco_ola,
        serie=serie_historico + serie_previsao,
        pressao_equipes=pressao_equipes,
        metodologia=metodologia_topo,
    )
