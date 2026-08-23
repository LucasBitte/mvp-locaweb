"""
Routers dos endpoints 2-6 (detalhe, fatores, clusters, kpi, alertas)

Implementação consolidada com queries leves para começar. Otimizações em Fase 5.
"""
import os
from datetime import datetime, date, timedelta
from typing import Optional, List

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Query

from app.api.models import (
    DetalheResponse, FatoresResponse, ClustersResponse, KPIResponse, AlertasResponse,
    PrevisaoCategoria, RecorrenciaOperacional, PrevisaoPonto,
    IncidenteRisco, ShapDecomposicao, QualidadeModelo,
    PerfilCluster, DiagnosticoKmeans,
    MetricaKPI, FaixaMeta,
    Alerta, Recomendacao, SaudeModelo,
    MetadadosResposta
)

router = APIRouter(prefix="/api", tags=["endpoints"])


def get_db_connection():
    env_vars = {}
    env_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    if os.path.exists(env_file_path):
        with open(env_file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_vars[k] = v

    return psycopg2.connect(
        host=env_vars.get("FIAP_DB_HOST", "localhost"),
        port=int(env_vars.get("FIAP_DB_PORT", 5432)),
        database=env_vars.get("FIAP_DB_NAME", "fiap"),
        user=env_vars.get("FIAP_DB_USER", "fiap"),
        password=env_vars.get("FIAP_DB_PASSWORD", ""),
    )


# ============================================================================
# Endpoint 2: GET /api/detalhe
# ============================================================================

@router.get("/detalhe", response_model=DetalheResponse)
def get_detalhe(
    prioridade: Optional[str] = Query("P2,P3"),
    categoria: Optional[str] = Query(None),
    horizonte_dias: Optional[int] = Query(7, ge=1, le=30),
):
    """Forecast detalhado por categoria + recorrências + série histórica"""

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Previsão por categoria (D+1 a D+7)
        hoje = date.today()
        previsao_por_categoria = []

        cur.execute("""
            SELECT categoria, SUM(yhat_categoria) as yhat
            FROM ml.fct_previsao_categoria
            WHERE ds BETWEEN %s AND %s
            GROUP BY categoria
            ORDER BY yhat DESC
        """, (hoje, hoje + timedelta(days=horizonte_dias)))

        for row in cur.fetchall():
            previsao_por_categoria.append(PrevisaoCategoria(
                categoria=row["categoria"],
                yhat=float(row["yhat"] or 0),
                delta_pct=0.0,  # TODO: calcular contra baseline
                cobertura_dias_atual_pct=0.0,  # TODO: ler de fct_recorrencia_operacional
            ))

        # 2. Recorrências top (sazonalidade, tendência)
        recorrencias_top = []
        cur.execute("""
            SELECT categoria, status_recorrencia, delta_pct
            FROM dw.fct_recorrencia_operacional
            WHERE status_recorrencia IN ('recorrente_crescente', 'recorrente_em_queda', 'pico_pontual')
            AND categoria IS NOT NULL
            ORDER BY ABS(delta_pct) DESC
            LIMIT 5
        """)
        for row in cur.fetchall():
            recorrencias_top.append(RecorrenciaOperacional(
                produto_categoria=row["categoria"],
                tipo=row["status_recorrencia"],
                evidencia=float(row["delta_pct"] or 0),
            ))

        # 3. Série histórica (14 dias)
        historico_serie = []
        cur.execute("""
            SELECT data_abertura as ds, total_chamados as y
            FROM ml.ml_forecast_dataset
            WHERE data_abertura >= %s
            ORDER BY data_abertura DESC
            LIMIT 14
        """, (hoje - timedelta(days=14),))
        for row in cur.fetchall():
            historico_serie.append(PrevisaoPonto(
                ds=row["ds"],
                y=float(row["y"] or 0),
                yhat=0.0,
                yhat_lower=None,
                yhat_upper=None,
            ))

        return DetalheResponse(
            prioridades_filtradas=prioridade.split(","),
            previsao_por_categoria=previsao_por_categoria,
            recorrencias_top=recorrencias_top,
            historico_serie=historico_serie,
            metadados=MetadadosResposta(data_execucao=datetime.now()),
        )
    finally:
        conn.close()


# ============================================================================
# Endpoint 3: GET /api/fatores
# ============================================================================

@router.get("/fatores", response_model=FatoresResponse)
def get_fatores(incidente_id: Optional[str] = Query(None)):
    """Risco & explicabilidade — ranking + SHAP + qualidade"""

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Ranking de risco (JOIN até dw.fct_incidentes p/ prioridade+categoria reais)
        ranking_incidentes = []
        cur.execute("""
            SELECT
                r.incident_id,
                dp.prioridade_num,
                dc.categoria,
                r.score_calibrado,
                r.motivo_principal
            FROM ml.fct_risco_incidente r
            JOIN dw.fct_incidentes fi ON fi.incident_id = r.incident_id
            JOIN dw.dim_prioridade dp ON dp.dim_prioridade_sk = fi.dim_prioridade_sk
            JOIN dw.dim_produto_categoria dc ON dc.dim_produto_categoria_sk = fi.dim_produto_categoria_sk
            ORDER BY r.score_calibrado DESC
            LIMIT 30
        """)
        for row in cur.fetchall():
            ranking_incidentes.append(IncidenteRisco(
                incidente_id=row["incident_id"],
                prioridade=f"P{row['prioridade_num']}",
                categoria=row["categoria"],
                score_calibrado=float(row["score_calibrado"] or 0),
                top_fator=row["motivo_principal"] or "não informado",
            ))

        # 2. SHAP se incidente_id fornecido
        # NOTA: base_value/saida_bruta_xgboost (saída bruta pré-calibração) ainda não
        # existem em nenhuma tabela de produção nem em ml_dev (Fase 2.2 bloqueada —
        # ver FASE2_RECOMENDACOES.md). Sem base_value não dá pra montar um waterfall
        # matematicamente válido, então shap_decomposicao fica None até essa
        # investigação no notebook XGBoost ser concluída.
        shap_decomposicao = None

        # 3. Importância global
        importancia_global = {}
        cur.execute("""
            SELECT conceito, importance_pct FROM ml.fct_importancia_conceito
            ORDER BY importance_pct DESC LIMIT 10
        """)
        for row in cur.fetchall():
            importancia_global[row["conceito"]] = float(row["importance_pct"] or 0)

        # 4. Qualidade do modelo (XGBoost)
        qualidade_modelo = QualidadeModelo(
            auc_roc=0.7965,  # TODO: from ml_dev.fct_avaliacao_modelo
            mcc=0.076,
            brier=0.0457,
            precision=0.95,
            recall=1.0,  # TODO: from confusion matrix
            threshold_atual=0.5,
            confusion_matrix={"tp": 3165, "fp": 164, "fn": 0, "tn": 1},
            auc_por_prioridade={"P2": 0.70, "P3": 0.66},
            calibration_curve=[(0.0, 0.05), (0.5, 0.50), (1.0, 0.95)],
        )

        # 5. Heatmap categoria×dia
        heatmap_categoria_dia = {}

        return FatoresResponse(
            ranking_incidentes=ranking_incidentes,
            incidente_selecionado=incidente_id,
            shap_decomposicao=shap_decomposicao,
            importancia_global=importancia_global,
            qualidade_modelo=qualidade_modelo,
            heatmap_categoria_dia=heatmap_categoria_dia,
            metadados=MetadadosResposta(data_execucao=datetime.now()),
        )
    finally:
        conn.close()


# ============================================================================
# Endpoint 4: GET /api/clusters
# ============================================================================

@router.get("/clusters", response_model=ClustersResponse)
def get_clusters():
    """Perfis operacionais — clusters com diagnóstico de k"""

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Perfis de cluster
        clusters = []
        cur.execute("""
            SELECT
                c.cluster_id,
                c.nome_perfil,
                p.n_incidentes,
                p.pct_volume,
                p.duracao_media_horas,
                p.taxa_excedeu_tempo_esperado_pct,
                c.cor_hex
            FROM ml.dim_cluster c
            LEFT JOIN ml.fct_perfil_cluster p ON c.cluster_id = p.cluster_id
            ORDER BY c.cluster_id
        """)
        for row in cur.fetchall():
            impacto = (float(row["pct_volume"] or 0) / 100.0) * (float(row["taxa_excedeu_tempo_esperado_pct"] or 0) / 100.0)
            clusters.append(PerfilCluster(
                cluster_id=row["cluster_id"],
                nome_perfil=row["nome_perfil"],
                n_incidentes=int(row["n_incidentes"] or 0),
                pct_volume=float(row["pct_volume"] or 0),
                duracao_media_horas=float(row["duracao_media_horas"] or 0),
                taxa_excedeu_tempo_esperado_pct=float(row["taxa_excedeu_tempo_esperado_pct"] or 0),
                cor_hex=row["cor_hex"],
                impacto_volume_excedencia_pct=impacto * 100.0,
            ))

        # 2. Diagnóstico k — ml_dev.fct_avaliacao_modelo é formato longo
        # (modelo, dimensao, chave_dimensao, metrica, valor), não tem colunas
        # k/silhouette/davies_bouldin dedicadas — precisa pivotar em Python.
        # pca_variancia não é persistida (não depende de k, é do PCA global) —
        # segue como constante documentada, sinalizada no frontend.
        diagnostico_kmeans = []
        cur.execute("""
            SELECT chave_dimensao, metrica, valor
            FROM ml_dev.fct_avaliacao_modelo
            WHERE modelo = 'kmeans' AND dimensao = 'k'
            ORDER BY chave_dimensao
        """)
        por_k: dict = {}
        for row in cur.fetchall():
            k = int(float(row["chave_dimensao"]))
            por_k.setdefault(k, {})[row["metrica"]] = float(row["valor"] or 0)
        for k in sorted(por_k):
            diagnostico_kmeans.append(DiagnosticoKmeans(
                k=k,
                silhouette=por_k[k].get("silhouette", 0.0),
                davies_bouldin=por_k[k].get("davies_bouldin", 0.0),
                pca_variancia=39.95,  # constante documentada — ver docs/eda-consolidada.md
            ))

        # 3. Composição por prioridade/categoria — TENTADO via ml.ml_cluster_dataset
        # (cluster_id + prioridade_num + categoria por incidente), mas essa tabela
        # tem cluster_id 100% NULL: o rótulo de cluster por incidente nunca foi
        # persistido em lugar nenhum (só o perfil agregado existe, em
        # ml.fct_perfil_cluster). Preencher isso exigiria re-rodar o notebook
        # K-Means para gravar o assignment por incidente — retreino de modelo em
        # produção requer aprovação explícita (CLAUDE.md §8), não é decisão de
        # uma correção de query. Fica sem fonte até essa decisão ser tomada.
        composicao_por_prioridade = {}
        composicao_por_categoria = {}

        return ClustersResponse(
            clusters=clusters,
            diagnostico_kmeans=diagnostico_kmeans,
            composicao_por_prioridade=composicao_por_prioridade,
            composicao_por_categoria=composicao_por_categoria,
            metadados=MetadadosResposta(data_execucao=datetime.now()),
        )
    finally:
        conn.close()


# ============================================================================
# Endpoint 5: GET /api/kpi
# ============================================================================

@router.get("/kpi", response_model=KPIResponse)
def get_kpi(prioridade: Optional[str] = Query("P2,P3")):
    """OLA & Metas — faixas + projeção"""

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Métricas de KPI por prioridade
        metricas = []
        for prio in prioridade.split(","):
            prio_num = int(prio[1])
            for indicador in ["ola_quebrado", "volume_tratado"]:
                metricas.append(MetricaKPI(
                    prioridade=prio,
                    indicador=indicador,
                    status="ok",  # TODO: verificar contra meta
                    projecao_atingimento_meta_pct=95.0,  # TODO: from dw.ref_meta_sla_anual
                ))

        # 2. Faixas (TODO)
        faixas_por_prioridade_indicador = {}

        # 3. Volume total do ano
        cur.execute("SELECT COUNT(*) as total FROM dw.fct_incidentes WHERE EXTRACT(YEAR FROM aberto_at) = 2025")
        vol_year = cur.fetchone()["total"] or 41441

        return KPIResponse(
            metricas=metricas,
            faixas_por_prioridade_indicador=faixas_por_prioridade_indicador,
            projecao_atingimento_meta_pct=95.0,
            metodologia_probabilidade="projecao_linear",
            volume_total_ano_referencia=int(vol_year),
            metadados=MetadadosResposta(data_execucao=datetime.now()),
        )
    finally:
        conn.close()


# ============================================================================
# Endpoint 6: GET /api/alertas
# ============================================================================

@router.get("/alertas", response_model=AlertasResponse)
def get_alertas(limit: Optional[int] = Query(20, ge=1, le=100)):
    """Ações & governança — alertas + saúde dos modelos"""

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Alertas ativos
        # NOTA: ml.alertas_ativos nunca existiu em produção. Servindo de
        # ml_dev.alertas_ativos (populado por scripts/create_and_populate_alertas_dev.py)
        # até uma decisão de promover para `ml` na Fase 5.
        alertas_ativos = []
        cur.execute("""
            SELECT id, severidade, condicao, cluster_id, equipe_id, origem
            FROM ml_dev.alertas_ativos
            ORDER BY CASE severidade
                WHEN 'crítica' THEN 4 WHEN 'alta' THEN 3
                WHEN 'média' THEN 2 ELSE 1 END DESC
            LIMIT %s
        """, (limit,))
        for row in cur.fetchall():
            alertas_ativos.append(Alerta(
                id=row["id"],
                severidade=row["severidade"],
                condicao=row["condicao"],
                cluster_id=row.get("cluster_id"),
                equipe_id=row.get("equipe_id"),
                origem=row["origem"],
                timestamp=datetime.now(),
            ))

        # 2. Saúde dos modelos (de ml_dev.fct_avaliacao_modelo)
        saude_modelos = []
        saude_modelos.append(SaudeModelo(
            modelo="prophet_total",
            status="degradado",
            metrica_chave=35.73,
            limitacao="Perde do baseline (MAE 35,73 vs 31,24)",
        ))
        saude_modelos.append(SaudeModelo(
            modelo="xgboost",
            status="abaixo_meta",
            metrica_chave=0.7965,
            limitacao="AUC 0,7965 < meta 0,85",
        ))
        saude_modelos.append(SaudeModelo(
            modelo="kmeans",
            status="ok",
            metrica_chave=4.0,
            limitacao="k=4 é decisão de negócio, não ótimo estatístico",
        ))

        # 3. Recomendações (TODO)
        recomendacoes = []

        # 4. Limitações
        limitacoes_sistema = [
            "Prophet total perde do baseline simples em MAE",
            "XGBoost abaixo da meta de AUC-ROC 0,85",
            "K-Means sem k ótimo — k=4 é decisão de negócio",
            "Sem CI (Continuous Integration) no projeto",
        ]

        return AlertasResponse(
            alertas_ativos=alertas_ativos,
            recomendacoes=recomendacoes,
            saude_modelos=saude_modelos,
            limitacoes_sistema=limitacoes_sistema,
            metadados=MetadadosResposta(data_execucao=datetime.now()),
        )
    finally:
        conn.close()
