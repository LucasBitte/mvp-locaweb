"""GET /api/alertas — tela Alertas/"Alertas & Ações" (PLAN.md Fase 11,
docs/prds/etapa5-api.md §4.6).

5 regras candidatas, cada alerta/recomendação carrega `regra_origem`
explícito. Nenhuma regra depende de item de configuração (CI) — recorrência
por CI continua fora de escopo (§3 do PRD).

`cluster_alta_violacao` usa a mesma métrica renomeada de `/api/clusters`
(`taxa_excedeu_tempo_esperado_pct`, ver `app/api/routers/clusters.py`) — o
texto do alerta evita a palavra "SLA" para não contradizer a tela KPI
(indicador oficial, `kpi_status_int`, ordens de grandeza menor).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.api.deps import get_db_engine

router = APIRouter(prefix="/api", tags=["alertas"])

# Limiares fixos, documentados aqui — não recalculados no frontend.
_PICO_CRITICO_PCT = 20.0
_PICO_ATENCAO_PCT = 10.0
_CONCENTRACAO_CATEGORIA_PCT = 15.0
_CLUSTER_TAXA_ALTA_PCT = 95.0  # ver caveat no docstring do módulo
_RECORRENCIA_GRANULARIDADES_SIMPLES = ("categoria", "produto")


class Alerta(BaseModel):
    tipo: Literal["critico", "atencao", "info"]
    regra_origem: str
    titulo: str
    mensagem: str


class Recomendacao(BaseModel):
    ordem: int
    texto: str
    prioridade: Literal["alta", "media", "baixa"]
    regra_origem: str


class AlertasResponse(BaseModel):
    alertas: list[Alerta]
    recomendacoes: list[Recomendacao]


def _fmt(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


@router.get("/alertas", response_model=AlertasResponse)
def get_alertas(engine: Engine = Depends(get_db_engine)) -> AlertasResponse:
    alertas: list[Alerta] = []
    recomendacoes: list[Recomendacao] = []

    with engine.connect() as conn:
        # 1. pico_volume_d1 — sempre presente (baseline informativo).
        origem_total = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_diaria_total")).scalar_one()
        yhat_d1 = conn.execute(
            text("SELECT yhat FROM ml.fct_previsao_diaria_total WHERE origem = :o AND horizonte = 'D+1'"),
            {"o": origem_total},
        ).scalar_one()
        media_historica_total = conn.execute(text("SELECT AVG(total_chamados) FROM ml.ml_forecast_dataset")).scalar_one()
        variacao_pico = (float(yhat_d1) - float(media_historica_total)) / float(media_historica_total) * 100
        if variacao_pico > _PICO_CRITICO_PCT:
            tipo_pico = "critico"
        elif variacao_pico > _PICO_ATENCAO_PCT:
            tipo_pico = "atencao"
        else:
            tipo_pico = "info"
        alertas.append(
            Alerta(
                tipo=tipo_pico,
                regra_origem="pico_volume_d1",
                titulo="Volume previsto para D+1" if tipo_pico == "info" else "Pico de volume previsto — D+1",
                mensagem=(
                    f"{_fmt(float(yhat_d1))} incidentes previstos para D+1 contra média histórica de "
                    f"{_fmt(float(media_historica_total))}/dia ({'+' if variacao_pico >= 0 else ''}{_fmt(variacao_pico)}%)."
                ),
            )
        )
        recomendacoes.append(
            Recomendacao(
                ordem=len(recomendacoes) + 1,
                texto=(
                    "Manter capacidade padrão para D+1; reavaliar se a previsão subir acima do limiar crítico."
                    if tipo_pico == "info"
                    else "Reforçar capacidade de plantão para D+1 — volume previsto significativamente acima da média histórica."
                ),
                prioridade="alta" if tipo_pico == "critico" else "media" if tipo_pico == "atencao" else "baixa",
                regra_origem="pico_volume_d1",
            )
        )

        # 2. pressao_operacional_equipe — só gerado se alguma equipe != 'normal'.
        origem_pressao = conn.execute(text("SELECT MAX(origem) FROM ml.fct_pressao_equipe")).scalar_one()
        equipes_pressao = conn.execute(
            text(
                """
                SELECT dg.grupo_designado, pe.pressao_relativa_pct, pe.nivel_pressao
                FROM ml.fct_pressao_equipe pe
                JOIN dw.dim_grupo dg ON pe.dim_grupo_sk = dg.dim_grupo_sk
                WHERE pe.origem = :o AND pe.h = 1 AND pe.nivel_pressao != 'normal'
                ORDER BY pe.pressao_relativa_pct DESC
                """
            ),
            {"o": origem_pressao},
        ).mappings().all()
        if equipes_pressao:
            top = equipes_pressao[0]
            tipo_pressao = "critico" if any(r["nivel_pressao"] == "critico" for r in equipes_pressao) else "atencao"
            outras = ", ".join(f"{r['grupo_designado']} ({'+' if r['pressao_relativa_pct'] >= 0 else ''}{_fmt(float(r['pressao_relativa_pct']))}%)" for r in equipes_pressao[1:4])
            alertas.append(
                Alerta(
                    tipo=tipo_pressao,
                    regra_origem="pressao_operacional_equipe",
                    titulo=f"{top['grupo_designado']} acima da própria média histórica",
                    mensagem=(
                        f"Volume previsto para D+1 em {top['grupo_designado']} está "
                        f"{'+' if top['pressao_relativa_pct'] >= 0 else ''}{_fmt(float(top['pressao_relativa_pct']))}% "
                        f"acima da média histórica da equipe (nível {top['nivel_pressao']})."
                        + (f" Também em atenção: {outras}." if outras else "")
                    ),
                )
            )
            recomendacoes.append(
                Recomendacao(
                    ordem=len(recomendacoes) + 1,
                    texto=f"Reforçar {top['grupo_designado']} no turno de D+1 e revisar a fila inicial.",
                    prioridade="alta" if tipo_pressao == "critico" else "media",
                    regra_origem="pressao_operacional_equipe",
                )
            )

        # 3. cluster_alta_violacao.
        data_execucao_cluster = conn.execute(text("SELECT MAX(data_execucao) FROM ml.fct_perfil_cluster")).scalar_one()
        clusters_altos = conn.execute(
            text(
                """
                SELECT d.cluster_id, d.nome_perfil, p.pct_volume, p.duracao_media_horas, p.taxa_sla_violado_pct
                FROM ml.fct_perfil_cluster p
                JOIN ml.dim_cluster d ON p.cluster_id = d.cluster_id
                WHERE p.data_execucao = :d AND p.taxa_sla_violado_pct > :limiar
                ORDER BY p.taxa_sla_violado_pct DESC
                """
            ),
            {"d": data_execucao_cluster, "limiar": _CLUSTER_TAXA_ALTA_PCT},
        ).mappings().all()
        if clusters_altos:
            top_cluster = clusters_altos[0]
            alertas.append(
                Alerta(
                    tipo="atencao",
                    regra_origem="cluster_alta_violacao",
                    titulo=f"Perfil operacional {top_cluster['cluster_id']} concentra tempo de atendimento acima do esperado",
                    mensagem=(
                        f"O cluster {top_cluster['cluster_id']} ({top_cluster['nome_perfil']}) responde por "
                        f"{_fmt(float(top_cluster['pct_volume']))}% do volume, com "
                        f"{_fmt(float(top_cluster['taxa_sla_violado_pct']))}% dos incidentes excedendo o tempo "
                        f"esperado da prioridade e duração média de {_fmt(float(top_cluster['duracao_media_horas']))}h."
                    ),
                )
            )
            recomendacoes.append(
                Recomendacao(
                    ordem=len(recomendacoes) + 1,
                    texto=f"Abrir força-tarefa sobre o cluster {top_cluster['cluster_id']} — priorizar os incidentes de maior duração.",
                    prioridade="alta",
                    regra_origem="cluster_alta_violacao",
                )
            )

        # 4. concentracao_categoria — sempre presente (baseline informativo).
        origem_cat = conn.execute(text("SELECT MAX(origem) FROM ml.fct_previsao_categoria")).scalar_one()
        top_categoria = conn.execute(
            text(
                """
                SELECT categoria, yhat_categoria
                FROM ml.fct_previsao_categoria
                WHERE origem = :o AND horizonte = 'D+1'
                ORDER BY yhat_categoria DESC
                LIMIT 1
                """
            ),
            {"o": origem_cat},
        ).mappings().first()
        participacao_categoria = float(top_categoria["yhat_categoria"]) / float(yhat_d1) * 100
        tipo_concentracao = "atencao" if participacao_categoria > _CONCENTRACAO_CATEGORIA_PCT else "info"
        alertas.append(
            Alerta(
                tipo=tipo_concentracao,
                regra_origem="concentracao_categoria",
                titulo=f"{top_categoria['categoria']} concentra o volume previsto de D+1",
                mensagem=(
                    f"{top_categoria['categoria']} responde por {_fmt(float(top_categoria['yhat_categoria']))} dos "
                    f"{_fmt(float(yhat_d1))} incidentes previstos para D+1 ({_fmt(participacao_categoria)}% do total)."
                ),
            )
        )
        recomendacoes.append(
            Recomendacao(
                ordem=len(recomendacoes) + 1,
                texto=f"Antecipar triagem de {top_categoria['categoria']} na abertura, roteirizando direto para a fila especializada.",
                prioridade="media" if tipo_concentracao == "atencao" else "baixa",
                regra_origem="concentracao_categoria",
            )
        )

        # 5. recorrencia_operacional — só gerado se houver entidade recorrente_crescente.
        janela_referencia = conn.execute(text("SELECT MAX(janela_referencia) FROM dw.fct_recorrencia_operacional")).scalar_one()
        recorrentes = conn.execute(
            text(
                """
                SELECT entidade, granularidade, delta_pct, cobertura_dias_atual_pct
                FROM dw.fct_recorrencia_operacional
                WHERE janela_referencia = :j
                  AND granularidade = ANY(:granularidades)
                  AND status_recorrencia = 'recorrente_crescente'
                ORDER BY delta_pct DESC
                LIMIT 1
                """
            ),
            {"j": janela_referencia, "granularidades": list(_RECORRENCIA_GRANULARIDADES_SIMPLES)},
        ).mappings().first()
        if recorrentes:
            alertas.append(
                Alerta(
                    tipo="atencao",
                    regra_origem="recorrencia_operacional",
                    titulo=f"{recorrentes['entidade']} recorrente e em crescimento",
                    mensagem=(
                        f"Volume de {recorrentes['entidade']} ({recorrentes['granularidade']}) cresceu "
                        f"{_fmt(float(recorrentes['delta_pct']))}% na janela de 30 dias, presente em "
                        f"{_fmt(float(recorrentes['cobertura_dias_atual_pct']))}% dos dias — padrão de recorrência, não pico isolado."
                    ),
                )
            )
            recomendacoes.append(
                Recomendacao(
                    ordem=len(recomendacoes) + 1,
                    texto=f"Tratar {recorrentes['entidade']} como problema, não como incidente isolado — abrir registro de problema.",
                    prioridade="alta",
                    regra_origem="recorrencia_operacional",
                )
            )

    return AlertasResponse(alertas=alertas, recomendacoes=recomendacoes)
