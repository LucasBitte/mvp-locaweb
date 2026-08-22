// Cliente HTTP para app/api (FastAPI, Etapa 5/PLAN.md Fase 14). Tipos espelham
// exatamente os pydantic.BaseModel de app/api/routers/*.py — qualquer mudança
// de contrato lá precisa ser refletida aqui.

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

async function apiGet<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(path, API_BASE_URL)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v))
    }
  }
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`${path} respondeu ${res.status}: ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// /api/painel
// ---------------------------------------------------------------------------

export interface PrevisaoPonto {
  valor: number
  data: string
  modelo_versao: string
  metodologia: string | null
  share_historico: number | null
}

export interface PrevisaoMedia {
  valor: number
  variacao_pct_vs_media_historica: number
}

export interface RiscoOla {
  nivel: 'baixo' | 'medio' | 'alto'
  pct_violacao_media_movel: number
  janela_dias: number
}

export interface SeriePonto {
  data: string
  tipo: 'historico' | 'previsao'
  valor: number
  horizonte: string | null
  metodologia: string | null
  share_historico: number | null
}

export interface PressaoEquipe {
  dim_grupo_sk: string
  grupo_designado: string
  yhat_previsto: number
  media_historica_diaria: number
  pressao_relativa_pct: number
  nivel_pressao: 'normal' | 'atencao' | 'critico'
  metodo_origem: string
}

export interface PainelResponse {
  previsao_d1: PrevisaoPonto
  previsao_d7_media: PrevisaoMedia
  risco_ola: RiscoOla
  serie: SeriePonto[]
  pressao_equipes: PressaoEquipe[]
  metodologia: string | null
}

export function getPainel(params?: { prioridade?: number; dias?: number }): Promise<PainelResponse> {
  return apiGet('/api/painel', params)
}

// ---------------------------------------------------------------------------
// /api/detalhe
// ---------------------------------------------------------------------------

export interface PrioridadeDetalhe {
  prioridade_num: number
  bucket_prioridade: string
  previsto: number
  threshold_sla_horas: number | null
  metodologia: string
  share_historico: number
  pct_limite_mensal: null
  is_placeholder_limite: boolean
}

export interface EntidadeDetalhe {
  nome: string
  yhat: number
  share_historico: number
  metodologia: string
}

export interface EntidadeRecorrente {
  entidade: string
  volume_atual: number
  volume_baseline: number
  delta_pct: number | null
  cobertura_dias_atual_pct: number
  status_recorrencia: string
}

export interface RecorrenciaBloco {
  granularidade: string
  janela_referencia: string
  entidades: EntidadeRecorrente[]
}

export interface DetalheResponse {
  prioridades: PrioridadeDetalhe[]
  agrupamento: 'categoria' | 'produto'
  top_entidades: EntidadeDetalhe[]
  recorrencia: RecorrenciaBloco
}

export function getDetalhe(params?: { horizonte?: string; agrupamento?: 'categoria' | 'produto' }): Promise<DetalheResponse> {
  return apiGet('/api/detalhe', params)
}

// ---------------------------------------------------------------------------
// /api/kpi
// ---------------------------------------------------------------------------

export interface Faixa {
  faixa_min: number | null
  faixa_max: number | null
  pct_atingimento: number
  ordem_faixa: number
}

export interface IndicadorKpi {
  prioridade_num: number
  bucket_prioridade: string
  indicador: 'ola_quebrado' | 'volume_tratado'
  contagem_acumulada_ano: number
  faixa: Faixa
  faixas: Faixa[]
  status: 'dentro_da_meta' | 'atencao' | 'critico'
  probabilidade_atingir_meta_pct: number
  metodologia_probabilidade: string
}

export interface KpiResponse {
  ano: number
  dias_decorridos: number
  dias_restantes: number
  indicadores: IndicadorKpi[]
}

export function getKpi(params?: { ano?: number }): Promise<KpiResponse> {
  return apiGet('/api/kpi', params)
}

// ---------------------------------------------------------------------------
// /api/fatores
// ---------------------------------------------------------------------------

export interface ImportanciaItem {
  conceito: string | null
  feature: string | null
  n_colunas: number | null
  importance_pct: number
  rank: number
}

export interface ShapItem {
  incident_id: string
  feature: string
  shap_value: number
  direcao: 'aumenta_risco' | 'reduz_risco'
  rank_abs: number
  score_calibrado: number
}

export interface HeatmapCelula {
  categoria: string
  dia_semana_num: number
  nome_dia: string
  volume_medio: number
}

export interface FatoresResponse {
  importancia_conceitos: ImportanciaItem[]
  granularidade: 'conceito' | 'coluna'
  shap_top_risco: ShapItem[]
  heatmap_categoria_dia: HeatmapCelula[]
}

export function getFatores(): Promise<FatoresResponse> {
  return apiGet('/api/fatores')
}

// ---------------------------------------------------------------------------
// /api/clusters
// ---------------------------------------------------------------------------

export interface ClusterItem {
  cluster_id: string
  nome_perfil: string
  descricao_curta: string
  tags: string[]
  cor_hex: string
  n_incidentes: number
  pct_volume: number
  duracao_media_horas: number | null
  taxa_resolucao_pct: number | null
  taxa_excedeu_tempo_esperado_pct: number | null
}

export interface ClustersResponse {
  clusters: ClusterItem[]
  modelo_versao: string
  data_execucao: string
  nota_metrica_sla: string
}

export function getClusters(): Promise<ClustersResponse> {
  return apiGet('/api/clusters')
}

// ---------------------------------------------------------------------------
// /api/alertas
// ---------------------------------------------------------------------------

export interface Alerta {
  tipo: 'critico' | 'atencao' | 'info'
  regra_origem: string
  titulo: string
  mensagem: string
}

export interface Recomendacao {
  ordem: number
  texto: string
  prioridade: 'alta' | 'media' | 'baixa'
  regra_origem: string
}

export interface AlertasResponse {
  alertas: Alerta[]
  recomendacoes: Recomendacao[]
}

export function getAlertas(): Promise<AlertasResponse> {
  return apiGet('/api/alertas')
}
