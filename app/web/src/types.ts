// Types para os endpoints da API

export interface PrevisaoPonto {
  ds: string;
  y: number;
  yhat: number;
  yhat_lower?: number;
  yhat_upper?: number;
}

export interface PainelResponse {
  total_chamados: number;
  kpi_status_agregado: number;
  previsao_d1: PrevisaoPonto;
  pressao_d1_a_d7_media: number;
  pressao_equipes: Array<{ grupo_id: string; pressao_relativa_pct: number; metodo_origem: string }>;
  volume_total_ano_referencia: number;
  forecast_top_categoria: string;
  risco_principal: string;
}

export interface DetalheResponse {
  prioridades_filtradas: string[];
  previsao_por_categoria: Array<{ categoria: string; yhat: number; delta_pct: number; cobertura_dias_atual_pct: number }>;
  recorrencias_top: Array<{ produto_categoria: string; tipo: string; evidencia: number }>;
  historico_serie: PrevisaoPonto[];
}

export interface Metadados {
  data_execucao: string;
  origem: string;
}

export interface IncidenteRisco {
  incidente_id: string;
  prioridade: string;
  categoria: string;
  score_calibrado: number;
  top_fator: string;
}

export interface ShapDecomposicao {
  base_value: number;
  shap_values: Record<string, number>;
  saida_bruta_xgboost: number;
  score_calibrado: number;
}

export interface QualidadeModelo {
  auc_roc: number;
  mcc: number;
  brier: number;
  precision: number;
  recall: number;
  threshold_atual: number;
  confusion_matrix: { tp: number; fp: number; fn: number; tn: number };
  auc_por_prioridade: Record<string, number>;
  calibration_curve: Array<[number, number]>;
}

export interface FatoresResponse {
  ranking_incidentes: IncidenteRisco[];
  incidente_selecionado: string | null;
  shap_decomposicao: ShapDecomposicao | null;
  importancia_global: Record<string, number>;
  qualidade_modelo: QualidadeModelo;
  heatmap_categoria_dia: Record<string, Record<string, number>>;
  metadados: Metadados;
}

export interface DiagnosticoKmeans {
  k: number;
  silhouette: number;
  davies_bouldin: number;
  pca_variancia: number;
}

export interface PerfilCluster {
  cluster_id: string;
  nome_perfil: string;
  n_incidentes: number;
  pct_volume: number;
  duracao_media_horas: number;
  taxa_excedeu_tempo_esperado_pct: number;
  cor_hex: string;
  impacto_volume_excedencia_pct: number;
}

export interface ClustersResponse {
  clusters: PerfilCluster[];
  diagnostico_kmeans: DiagnosticoKmeans[];
  composicao_por_prioridade: Record<string, Record<string, number>>;
  composicao_por_categoria: Record<string, Record<string, number>>;
  metadados: Metadados;
}

export interface FaixaMeta {
  limite_inferior: number;
  limite_superior: number;
  cor_hex: string;
}

export interface MetricaKPI {
  prioridade: string;
  indicador: string;
  status: string;
  projecao_atingimento_meta_pct: number;
}

export interface KPIResponse {
  metricas: MetricaKPI[];
  faixas_por_prioridade_indicador: Record<string, FaixaMeta[]>;
  projecao_atingimento_meta_pct: number;
  metodologia_probabilidade: string;
  volume_total_ano_referencia: number;
  metadados: Metadados;
}

export interface Alerta {
  id: string;
  severidade: string;
  condicao: string;
  cluster_id: string | null;
  equipe_id: string | null;
  origem: string;
  timestamp: string;
}

export interface Recomendacao {
  id: string;
  acao: string;
  owner: string;
  prioridade: string;
  origem: string;
}

export interface SaudeModelo {
  modelo: string;
  status: string;
  metrica_chave: number;
  limitacao: string;
}

export interface AlertasResponse {
  alertas_ativos: Alerta[];
  recomendacoes: Recomendacao[];
  saude_modelos: SaudeModelo[];
  limitacoes_sistema: string[];
  metadados: Metadados;
}
