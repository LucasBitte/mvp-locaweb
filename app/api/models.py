"""
Modelos Pydantic para os 6 endpoints da API AIOps

Estrutura: BaseModel para cada tipo, agrupados por endpoint.
Cada modelo reflete a estrutura JSON que o frontend espera.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
from pydantic import BaseModel, Field


# ============================================================================
# Tipos Comuns
# ============================================================================

class MetadadosResposta(BaseModel):
    """Metadados incluídos em toda resposta"""
    data_execucao: datetime
    origem: str = "DADOS REAIS · API · FASE 16"


# ============================================================================
# Endpoint 1: /api/painel
# ============================================================================

class PrevisaoPonto(BaseModel):
    """Previsão pontual com intervalo de confiança"""
    ds: date
    y: float = Field(..., description="Volume histórico ou atual")
    yhat: float = Field(..., description="Predição point")
    yhat_lower: Optional[float] = Field(None, description="Intervalo 80% inferior")
    yhat_upper: Optional[float] = Field(None, description="Intervalo 80% superior")


class PressaoEquipe(BaseModel):
    """Pressão relativa de uma equipe vs. próprio histórico"""
    grupo_id: str
    pressao_relativa_pct: float
    metodo_origem: str = Field(..., description="prophet_individual|prophet_semanal|split_proporcional")


class PainelResponse(BaseModel):
    """Resposta de /api/painel — cockpit executivo"""
    total_chamados: int = Field(..., description="Volume de hoje")
    kpi_status_agregado: float = Field(..., description="% de OLA cumprido (P2+P3)")
    previsao_d1: PrevisaoPonto = Field(..., description="Previsão para amanhã")
    pressao_d1_a_d7_media: float = Field(..., description="Pressão média D+1..D+7")
    pressao_equipes: List[PressaoEquipe] = Field(..., description="Pressão por equipe")
    volume_total_ano_referencia: int = Field(..., description="Volume total do ano (baseline)")
    forecast_top_categoria: str = Field(..., description="Categoria com maior volume previsto")
    risco_principal: str = Field(..., description="Cluster ou feature de maior risco")
    metadados: MetadadosResposta


# ============================================================================
# Endpoint 2: /api/detalhe
# ============================================================================

class PrevisaoCategoria(BaseModel):
    """Previsão desagregada por categoria"""
    categoria: str
    yhat: float
    delta_pct: float = Field(..., description="% de crescimento vs. baseline")
    cobertura_dias_atual_pct: float = Field(..., description="Recorrência: dias com evento / 30")


class RecorrenciaOperacional(BaseModel):
    """Padrão de recorrência detectado"""
    produto_categoria: str
    tipo: str = Field(..., description="tendencia|sazonal|erro")
    evidencia: float


class DetalheResponse(BaseModel):
    """Resposta de /api/detalhe — forecast desagregado"""
    prioridades_filtradas: List[str]
    previsao_por_categoria: List[PrevisaoCategoria]
    recorrencias_top: List[RecorrenciaOperacional]
    historico_serie: List[PrevisaoPonto] = Field(..., description="14 dias atrás até hoje")
    metadados: MetadadosResposta


# ============================================================================
# Endpoint 3: /api/fatores (Risco & Explicabilidade)
# ============================================================================

class ShapDecomposicao(BaseModel):
    """Decomposição SHAP de um incidente (waterfall)"""
    base_value: float = Field(..., description="Saída BRUTA do XGBoost (não calibrada)")
    shap_values: Dict[str, float] = Field(..., description="{feature: contribution}")
    saida_bruta_xgboost: float
    score_calibrado: float = Field(..., description="Saída após calibrador isotônico")


class QualidadeModelo(BaseModel):
    """Métricas de qualidade do XGBoost"""
    auc_roc: float
    mcc: float = Field(..., description="Matthews Correlation Coefficient (métrica mais honesta que F1)")
    brier: float
    precision: float
    recall: float
    threshold_atual: float = Field(..., description="Threshold em produção")
    confusion_matrix: Dict[str, int] = Field(..., description="{tn, fp, fn, tp}")
    auc_por_prioridade: Dict[str, float] = Field(..., description="AUC por P2/P3/etc")
    calibration_curve: List[Tuple[float, float]] = Field(..., description="[(pred_prob, true_freq), ...]")


class IncidenteRisco(BaseModel):
    """Item no ranking de risco"""
    incidente_id: str
    prioridade: str
    categoria: str
    score_calibrado: float
    top_fator: str = Field(..., description="Feature de maior contribuição")


class FatoresResponse(BaseModel):
    """Resposta de /api/fatores — risco & explicabilidade"""
    ranking_incidentes: List[IncidenteRisco] = Field(..., description="Top N incidentes por risco")
    incidente_selecionado: Optional[str] = Field(None, description="ID do incidente se param fornecido")
    shap_decomposicao: Optional[ShapDecomposicao] = Field(None, description="Se incidente_id fornecido")
    importancia_global: Dict[str, float] = Field(..., description="{conceito: importancia_pct}")
    qualidade_modelo: QualidadeModelo
    heatmap_categoria_dia: Dict[str, Dict[str, float]] = Field(..., description="{categoria: {dia: vol_medio}}")
    metadados: MetadadosResposta


# ============================================================================
# Endpoint 4: /api/clusters (Perfis Operacionais)
# ============================================================================

class DiagnosticoKmeans(BaseModel):
    """Diagnóstico de k (silhueta, Davies-Bouldin)"""
    k: int
    silhouette: float
    davies_bouldin: float
    pca_variancia: float = Field(..., description="% de variância explicada por PC1+PC2")


class PerfilCluster(BaseModel):
    """Perfil de um cluster"""
    cluster_id: str
    nome_perfil: str
    n_incidentes: int
    pct_volume: float
    duracao_media_horas: float
    taxa_excedeu_tempo_esperado_pct: float
    cor_hex: str
    impacto_volume_excedencia_pct: float = Field(..., description="pct_volume × taxa (regra inicial)")


class ClustersResponse(BaseModel):
    """Resposta de /api/clusters — perfis operacionais"""
    clusters: List[PerfilCluster]
    diagnostico_kmeans: List[DiagnosticoKmeans] = Field(..., description="k=2..8")
    composicao_por_prioridade: Dict[str, Dict[str, float]] = Field(..., description="{cluster_id: {P2: %, P3: %}}")
    composicao_por_categoria: Dict[str, Dict[str, float]] = Field(..., description="{cluster_id: {categoria: %}}")
    metadados: MetadadosResposta


# ============================================================================
# Endpoint 5: /api/kpi (OLA & Metas)
# ============================================================================

class FaixaMeta(BaseModel):
    """Faixa de meta de SLA"""
    limite_inferior: float
    limite_superior: float
    cor_hex: str


class MetricaKPI(BaseModel):
    """Uma métrica de KPI (OLA por prioridade × indicador)"""
    prioridade: str
    indicador: str = Field(..., description="ola_quebrado|volume_tratado")
    status: str = Field(..., description="ok|warning|crítico")
    projecao_atingimento_meta_pct: float = Field(..., description="Projeção linear (determinística)")


class KPIResponse(BaseModel):
    """Resposta de /api/kpi — OLA & Metas"""
    metricas: List[MetricaKPI]
    faixas_por_prioridade_indicador: Dict[str, List[FaixaMeta]]
    projecao_atingimento_meta_pct: float = Field(..., description="Agregado (P2+P3)")
    metodologia_probabilidade: str = Field(default="projecao_linear", description="Método: determinístico, nunca probabilístico")
    volume_total_ano_referencia: int
    metadados: MetadadosResposta


# ============================================================================
# Endpoint 6: /api/alertas (Ações & Governança)
# ============================================================================

class Alerta(BaseModel):
    """Alerta ativo"""
    id: str
    severidade: str = Field(..., description="baixa|média|alta|crítica")
    condicao: str = Field(..., description="Descrição legível")
    cluster_id: Optional[str] = None
    equipe_id: Optional[str] = None
    origem: str = Field(..., description="regra ou modelo")
    timestamp: datetime


class Recomendacao(BaseModel):
    """Recomendação de ação"""
    id: str
    acao: str = Field(..., description="Descrição da ação")
    owner: str = Field(..., description="Responsável (equipe/role)")
    prioridade: str
    origem: str = Field(..., description="regra ou modelo")


class SaudeModelo(BaseModel):
    """Estado de saúde de um modelo"""
    modelo: str = Field(..., description="prophet|xgboost|kmeans")
    status: str = Field(..., description="ok|degradado|abaixo_meta")
    metrica_chave: float
    limitacao: str = Field(..., description="Limitação conhecida do modelo")


class AlertasResponse(BaseModel):
    """Resposta de /api/alertas — ações & governança"""
    alertas_ativos: List[Alerta]
    recomendacoes: List[Recomendacao]
    saude_modelos: List[SaudeModelo]
    limitacoes_sistema: List[str] = Field(..., description="Limitações declaradas do sistema")
    metadados: MetadadosResposta
