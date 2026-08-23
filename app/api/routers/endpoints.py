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
            SELECT categoria, SUM(yhat) as yhat
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
            SELECT produto_categoria, tipo, evidencia_pct
            FROM dw.fct_recorrencia_operacional
            WHERE tipo IN ('tendencia', 'sazonal')
            ORDER BY evidencia_pct DESC
            LIMIT 5
        """)
        for row in cur.fetchall():
            recorrencias_top.append(RecorrenciaOperacional(
                produto_categoria=row["produto_categoria"],
                tipo=row["tipo"],
                evidencia=float(row["evidencia_pct"] or 0),
            ))

        # 3. Série histórica (14 dias)
        historico_serie = []
        cur.execute("""
            SELECT ds, y, NULL::float as yhat, NULL::float as yhat_lower, NULL::float as yhat_upper
            FROM ml.ml_forecast_dataset
            WHERE ds >= %s
            ORDER BY ds DESC
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
def get_fatores(incidente_id: Optional[int] = Query(None)):
    """Risco & explicabilidade — ranking + SHAP + qualidade"""

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Ranking de risco
        ranking_incidentes = []
        cur.execute("""
            SELECT incidente_id, prioridade_num, categoria, score_calibrado
            FROM ml.fct_risco_incidente
            ORDER BY score_calibrado DESC
            LIMIT 30
        """)
        for row in cur.fetchall():
            ranking_incidentes.append(IncidenteRisco(
                incidente_id=row["incidente_id"],
                prioridade=f"P{row['prioridade_num']}",
                categoria=row["categoria"],
                score_calibrado=float(row["score_calibrado"] or 0),
                top_fator="prioridade",  # TODO: from fct_shap_incidente
            ))

        # 2. SHAP se incidente_id fornecido
        shap_decomposicao = None
        if incidente_id:
            cur.execute("""
                SELECT base_value, shap_value, saida_bruta_xgboost, score_calibrado
                FROM ml.fct_shap_incidente
                WHERE incidente_id = %s
                LIMIT 1
            """, (incidente_id,))
            shap_row = cur.fetchone()
            if shap_row:
                shap_decomposicao = ShapDecomposicao(
                    base_value=float(shap_row["base_value"] or 0),
                    shap_values={"feature1": 0.05},  # TODO: desagregar
                    saida_bruta_xgboost=float(shap_row["saida_bruta_xgboost"] or 0),
                    score_calibrado=float(shap_row["score_calibrado"] or 0),
                )

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
                p.taxa_sla_violado_pct,
                c.cor_hex
            FROM ml.dim_cluster c
            LEFT JOIN ml.fct_perfil_cluster p ON c.cluster_id = p.cluster_id
            ORDER BY c.cluster_id
        """)
        for row in cur.fetchall():
            impacto = (float(row["pct_volume"] or 0) / 100.0) * (float(row["taxa_sla_violado_pct"] or 0) / 100.0)
            clusters.append(PerfilCluster(
                cluster_id=row["cluster_id"],
                nome_perfil=row["nome_perfil"],
                n_incidentes=int(row["n_incidentes"] or 0),
                pct_volume=float(row["pct_volume"] or 0),
                duracao_media_horas=float(row["duracao_media_horas"] or 0),
                taxa_excedeu_tempo_esperado_pct=float(row["taxa_sla_violado_pct"] or 0),
                cor_hex=row["cor_hex"],
                impacto_volume_excedencia_pct=impacto * 100.0,
            ))

        # 2. Diagnóstico k
        diagnostico_kmeans = []
        cur.execute("""
            SELECT k, silhouette, davies_bouldin, pca_variancia
            FROM ml_dev.fct_avaliacao_modelo
            WHERE modelo = 'kmeans' AND dimensao = 'k'
            ORDER BY k
        """)
        for row in cur.fetchall():
            diagnostico_kmeans.append(DiagnosticoKmeans(
                k=int(row["k"]),
                silhouette=float(row["silhouette"] or 0),
                davies_bouldin=float(row["davies_bouldin"] or 0),
                pca_variancia=39.95,  # TODO: from tabela
            ))

        # 3. Composição (TODO)
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
        alertas_ativos = []
        cur.execute("""
            SELECT id, severidade, condicao, cluster_id, origem
            FROM ml.alertas_ativos
            ORDER BY severidade DESC
            LIMIT %s
        """, (limit,))
        for row in cur.fetchall():
            alertas_ativos.append(Alerta(
                id=row["id"],
                severidade=row["severidade"],
                condicao=row["condicao"],
                cluster_id=row.get("cluster_id"),
                equipe_id=None,
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
