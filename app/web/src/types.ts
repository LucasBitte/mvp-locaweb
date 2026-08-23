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

export interface FatoresResponse {
  ranking_incidentes: Array<{ incidente_id: number; prioridade: string; categoria: string; score_calibrado: number; top_fator: string }>;
  importancia_global: Record<string, number>;
  qualidade_modelo: {
    auc_roc: number;
    mcc: number;
    brier: number;
  };
}

export interface ClustersResponse {
  clusters: Array<{
    cluster_id: string;
    nome_perfil: string;
    n_incidentes: number;
    pct_volume: number;
    duracao_media_horas: number;
    taxa_excedeu_tempo_esperado_pct: number;
  }>;
}

export interface KPIResponse {
  metricas: Array<{ prioridade: string; indicador: string; status: string; projecao_atingimento_meta_pct: number }>;
  projecao_atingimento_meta_pct: number;
  volume_total_ano_referencia: number;
}

export interface AlertasResponse {
  alertas_ativos: Array<{ id: string; severidade: string; condicao: string; origem: string }>;
  saude_modelos: Array<{ modelo: string; status: string; metrica_chave: number; limitacao: string }>;
  limitacoes_sistema: string[];
}
