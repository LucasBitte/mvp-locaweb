// Funções puras de apresentação: recebem a resposta real de app/api/routers/*
// (ver src/lib/api.ts) e devolvem estruturas prontas para renderizar (posições
// de SVG, cores, texto formatado). Nenhuma delas busca dado — quem chama
// (as telas em components/screens/) já tem o payload da API em mãos.
//
// Antes desta versão este arquivo continha os números de uma execução real do
// pipeline, mas fixos (Etapa 5 ainda não existia). Religado à API em
// 2026-08-22 (PLAN.md Fase 15/religar) — a partir daqui os números vêm ao
// vivo do banco `fiap` a cada carregamento de tela.

import type {
  Alerta,
  ClusterItem,
  EntidadeDetalhe,
  EntidadeRecorrente,
  Faixa,
  HeatmapCelula,
  ImportanciaItem,
  IndicadorKpi,
  KpiResponse,
  PressaoEquipe,
  PrioridadeDetalhe,
  Recomendacao,
  SeriePonto,
  ShapItem,
} from '../lib/api'
import { AMBER, AMBER_FILL, BLUE, GREEN, RED, SUB } from '../lib/theme'

const fmtNum = (v: number) => Math.round(v).toLocaleString('pt-BR')
const fmt1 = (v: number) => v.toFixed(1).replace('.', ',')
const fmt2 = (v: number) => v.toFixed(2).replace('.', ',')
const sinal = (v: number) => (v >= 0 ? '+' : '')
const fmtDia = (iso: string) => {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

// Volume total real de dw.fct_incidentes em 2025 (41.441 linhas) — constante
// histórica de um ano já encerrado, não um valor que a API precisa recalcular
// a cada request (ver docs/eda-consolidada.md). Usada só para converter
// `share_historico` em contagem aproximada nas telas Painel/Detalhe.
export const VOLUME_HISTORICO_2025 = 41441

// ---------------------------------------------------------------------------
// Painel
// ---------------------------------------------------------------------------

export interface HistPoint {
  x: number
  y: number
  label: string
}

export interface GridLine {
  y: number
  ty: number
  label: string
}

export interface ForecastBar {
  x: number
  cx: number
  y: number
  h: number
  v: string
  vy: number
  label: string
  fill: string
}

export interface TeamRow {
  name: string
  pct: string
  w: string
  fill: string
  badge: string
  badgeBg: string
  badgeFg: string
}

/** `pontos` = SeriePonto[] com tipo === 'historico', em ordem cronológica. */
export function computeHistorico(pontos: SeriePonto[]) {
  const X0 = 44, X1 = 772, Y0 = 12, Y1 = 182
  const valores = pontos.map((p) => p.valor)
  const lo = Math.min(...valores)
  const hi = Math.max(...valores)
  const pad = Math.max(1, (hi - lo) * 0.1)
  const LO = Math.max(0, Math.floor(lo - pad))
  const HI = Math.ceil(hi + pad)
  const px = (i: number) => X0 + (i * (X1 - X0)) / Math.max(1, pontos.length - 1)
  const py = (v: number) => Y0 + (1 - (v - LO) / (HI - LO)) * (Y1 - Y0)
  const pts: HistPoint[] = pontos.map((p, i) => ({
    x: +px(i).toFixed(1),
    y: +py(p.valor).toFixed(1),
    label: fmtDia(p.data),
  }))
  const linePts = pts.map((p) => `${p.x},${p.y}`).join(' ')
  const areaPath = pts.length
    ? `M${pts[0].x},${Y1} ${pts.map((p) => `L${p.x},${p.y}`).join(' ')} L${pts[pts.length - 1].x},${Y1} Z`
    : ''
  const grid: GridLine[] = [0, 1 / 3, 2 / 3, 1].map((t) => {
    const v = LO + t * (HI - LO)
    const y = py(v)
    return { y: +y.toFixed(1), ty: +(y + 3.5).toFixed(1), label: fmtNum(v) }
  })
  // só rotula ~8 pontos no eixo X para não sobrepor texto quando `dias` é grande
  const passo = Math.max(1, Math.ceil(pts.length / 8))
  const ptsRotulados = pts.map((p, i) => ({ ...p, label: i % passo === 0 ? p.label : '' }))
  return { pts: ptsRotulados, linePts, areaPath, grid, Y1 }
}

/** `pontos` = SeriePonto[] com tipo === 'previsao' (D+1..D+7), `mediaD7` = previsao_d7_media.valor. */
export function computeForecastBars(pontos: SeriePonto[], mediaD7: number) {
  const FLO_RAW = Math.min(...pontos.map((p) => p.valor), mediaD7)
  const FHI_RAW = Math.max(...pontos.map((p) => p.valor), mediaD7)
  const pad = Math.max(1, (FHI_RAW - FLO_RAW) * 0.2)
  const FLO = Math.max(0, FLO_RAW - pad)
  const FHI = FHI_RAW + pad
  const FY0 = 24, FY1 = 182
  const fy = (v: number) => FY0 + (1 - (v - FLO) / (FHI - FLO)) * (FY1 - FY0)
  const fc: ForecastBar[] = pontos.map((p, i) => {
    const x = 8 + i * 53
    const y = +fy(p.valor).toFixed(1)
    return {
      x,
      cx: x + 19,
      y,
      h: +(FY1 - y).toFixed(1),
      v: fmt1(p.valor),
      vy: +(y - 7).toFixed(1),
      label: p.horizonte ?? `D+${i + 1}`,
      fill: i === 0 ? BLUE : 'rgba(30,111,217,.35)',
    }
  })
  const fcAvgY = +fy(mediaD7).toFixed(1)
  return { fc, fcAvgY, FY1 }
}

const NIVEL_PRESSAO_LABEL: Record<PressaoEquipe['nivel_pressao'], string> = {
  critico: 'crítico',
  atencao: 'atenção',
  normal: 'normal',
}

export function computeTeamPressure(equipes: PressaoEquipe[], limiarCritico: number): { rows: TeamRow[]; maxAbs: number } {
  const maxAbs = Math.max(limiarCritico * 1.3, ...equipes.map((e) => Math.abs(e.pressao_relativa_pct)), 1)
  const rows = equipes.map((e) => {
    const p = e.pressao_relativa_pct
    const critico = e.nivel_pressao === 'critico'
    const atencao = e.nivel_pressao === 'atencao'
    const up = p > 0
    return {
      name: e.grupo_designado,
      pct: sinal(p) + fmt1(p) + '%',
      w: `${Math.min(100, (Math.abs(p) / maxAbs) * 100).toFixed(1)}%`,
      fill: critico ? RED : atencao ? AMBER_FILL : up ? BLUE : GREEN,
      badge: critico ? 'crítico' : atencao ? 'atenção' : up ? 'normal' : 'abaixo da média',
      badgeBg: critico ? 'rgba(214,69,69,.12)' : atencao ? 'rgba(232,163,23,.14)' : 'rgba(15,157,88,.12)',
      badgeFg: critico ? RED : atencao ? AMBER : GREEN,
    }
  })
  return { rows, maxAbs }
}

export function nivelPressaoLabel(nivel: PressaoEquipe['nivel_pressao']): string {
  return NIVEL_PRESSAO_LABEL[nivel]
}

const RISCO_OLA_LABEL: Record<'baixo' | 'medio' | 'alto', { label: string; color: string }> = {
  baixo: { label: 'Baixo', color: GREEN },
  medio: { label: 'Médio', color: AMBER },
  alto: { label: 'Alto', color: RED },
}

export function riscoOlaVisual(nivel: 'baixo' | 'medio' | 'alto') {
  return RISCO_OLA_LABEL[nivel]
}

// ---------------------------------------------------------------------------
// Detalhe
// ---------------------------------------------------------------------------

const SUB_COLOR = '#7A8498'
const NAVY_COLOR = '#101C2E'

export function computePrioridadeFiltro() {
  return ['Todas', 'P1', 'P2', 'P3', 'P4'].map((label) => {
    const on = label === 'P2' || label === 'P3'
    return { label, bg: on ? '#FFFFFF' : 'transparent', fg: on ? NAVY_COLOR : SUB_COLOR, shadow: on ? '0 4px 16px rgba(10,22,40,.06)' : 'none' }
  })
}

/** Resume o banner "P2 + P3 — X% do volume total" a partir de share_historico real. */
export function computeFocoP2P3(prioridades: PrioridadeDetalhe[]) {
  const shareP2P3 = prioridades
    .filter((p) => p.prioridade_num === 2 || p.prioridade_num === 3)
    .reduce((acc, p) => acc + p.share_historico, 0)
  const n = Math.round(shareP2P3 * VOLUME_HISTORICO_2025)
  return { pct: fmt1(shareP2P3 * 100), n: fmtNum(n), total: fmtNum(VOLUME_HISTORICO_2025) }
}

export function computeMixHistorico(prioridades: PrioridadeDetalhe[]) {
  const ordenado = [...prioridades].sort((a, b) => a.prioridade_num - b.prioridade_num)
  const maxShare = Math.max(...ordenado.map((p) => p.share_historico), 0.0001)
  return ordenado.map((p) => {
    const pct = p.share_historico * 100
    const n = Math.round(p.share_historico * VOLUME_HISTORICO_2025)
    const destaque = p.prioridade_num === 2 || p.prioridade_num === 3
    return {
      p: `P${p.prioridade_num}`,
      n: fmtNum(n),
      pct: `${fmt1(pct)}%`,
      w: `${((p.share_historico / maxShare) * 100).toFixed(1)}%`,
      fill: destaque ? BLUE : 'rgba(30,111,217,.3)',
    }
  })
}

export function computeTopCategorias(entidades: EntidadeDetalhe[]) {
  const max = Math.max(...entidades.map((e) => e.yhat), 0.0001)
  return entidades.map((e) => ({ name: e.nome, v: fmt1(e.yhat), w: `${((e.yhat / max) * 100).toFixed(1)}%` }))
}

export function computeTopProdutos(entidades: EntidadeDetalhe[]) {
  const max = Math.max(...entidades.map((e) => e.yhat), 0.0001)
  return entidades.map((e) => ({
    name: e.nome,
    share: `${fmt1(e.share_historico * 100)}%`,
    pred: fmt1(e.yhat),
    w: `${((e.yhat / max) * 100).toFixed(1)}%`,
  }))
}

const RECORRENCIA_VISUAL: Record<string, { badge: string; badgeBg: string; badgeFg: string; note: string }> = {
  recorrente_crescente: {
    badge: 'recorrente crescente',
    badgeBg: 'rgba(214,69,69,.12)',
    badgeFg: RED,
    note: 'crescimento sustentado, não pico isolado',
  },
  recorrente_estavel: {
    badge: 'recorrente estável',
    badgeBg: 'rgba(232,163,23,.14)',
    badgeFg: AMBER,
    note: 'presença regular na janela, sem tendência de queda',
  },
}

export function computeRecorrencia(entidades: EntidadeRecorrente[]) {
  return entidades.map((e) => {
    const visual = RECORRENCIA_VISUAL[e.status_recorrencia] ?? {
      badge: e.status_recorrencia,
      badgeBg: 'rgba(10,22,40,.06)',
      badgeFg: SUB,
      note: '',
    }
    return {
      name: e.entidade,
      delta: e.delta_pct === null ? '—' : `${sinal(e.delta_pct)}${fmt1(e.delta_pct)}%`,
      days: `${fmt1(e.cobertura_dias_atual_pct)}%`,
      badge: visual.badge,
      badgeBg: visual.badgeBg,
      badgeFg: visual.badgeFg,
      note: visual.note,
    }
  })
}

// ---------------------------------------------------------------------------
// KPI
// ---------------------------------------------------------------------------

const INDICADOR_LABEL: Record<IndicadorKpi['indicador'], string> = {
  ola_quebrado: 'OLA quebrado',
  volume_tratado: 'Volume tratado',
}
const INDICADOR_UNIDADE: Record<IndicadorKpi['indicador'], string> = {
  ola_quebrado: 'quebras',
  volume_tratado: 'chamados tratados',
}
const STATUS_COR: Record<IndicadorKpi['status'], { bg: string; fg: string; label: string }> = {
  dentro_da_meta: { bg: 'rgba(15,157,88,.12)', fg: GREEN, label: 'dentro da meta' },
  atencao: { bg: 'rgba(232,163,23,.14)', fg: AMBER, label: 'atenção' },
  critico: { bg: 'rgba(214,69,69,.12)', fg: RED, label: 'crítico' },
}

function formatFaixaRange(f: Faixa): string {
  if (f.faixa_min === null) return `≤ ${fmtNum(f.faixa_max ?? 0)}`
  if (f.faixa_max === null) return `≥ ${fmtNum(f.faixa_min)}`
  return `${fmtNum(f.faixa_min)}–${fmtNum(f.faixa_max)}`
}

export function computeBandasMeta(indicadores: IndicadorKpi[]) {
  return indicadores.map((ind) => {
    const cor = STATUS_COR[ind.status]
    return {
      key: `${ind.prioridade_num}-${ind.indicador}`,
      prio: ind.bucket_prioridade,
      indicadorLabel: INDICADOR_LABEL[ind.indicador],
      cur: `${fmtNum(ind.contagem_acumulada_ano)} ${INDICADOR_UNIDADE[ind.indicador]}`,
      att: `${fmt1(ind.faixa.pct_atingimento)}%`,
      badgeBg: cor.bg,
      badgeFg: cor.fg,
      cells: ind.faixas.map((f) => {
        const on = f.ordem_faixa === ind.faixa.ordem_faixa
        const c = f.pct_atingimento >= 100 ? GREEN : f.pct_atingimento >= 50 ? AMBER_FILL : RED
        const cBg = f.pct_atingimento >= 100 ? 'rgba(15,157,88,.10)' : f.pct_atingimento >= 50 ? 'rgba(232,163,23,.12)' : 'rgba(214,69,69,.10)'
        return {
          att: `${fmt1(f.pct_atingimento)}%`,
          range: formatFaixaRange(f),
          bg: on ? cBg : '#F9F9FF',
          ring: on ? `2px solid ${c}` : '0px solid transparent',
        }
      }),
    }
  })
}

export function computeKpiResumo(kpi: KpiResponse) {
  const olaQuebrado = kpi.indicadores.filter((i) => i.indicador === 'ola_quebrado')
  const totalQuebras = olaQuebrado.reduce((acc, i) => acc + i.contagem_acumulada_ano, 0)
  const piorStatus: IndicadorKpi['status'] = kpi.indicadores.some((i) => i.status === 'critico')
    ? 'critico'
    : kpi.indicadores.some((i) => i.status === 'atencao')
      ? 'atencao'
      : 'dentro_da_meta'
  const probMedia = olaQuebrado.reduce((acc, i) => acc + i.probabilidade_atingir_meta_pct, 0) / Math.max(1, olaQuebrado.length)
  const diasTotais = kpi.dias_decorridos + kpi.dias_restantes
  return {
    ano: kpi.ano,
    diasDecorridos: kpi.dias_decorridos,
    diasTotais,
    diasRestantes: kpi.dias_restantes,
    totalQuebras: fmtNum(totalQuebras),
    quebrasPorPrioridade: olaQuebrado.map((i) => `${i.bucket_prioridade}: ${fmtNum(i.contagem_acumulada_ano)}`).join(' · '),
    statusGeral: STATUS_COR[piorStatus],
    probabilidadeMedia: fmt1(probMedia),
  }
}

export function computeProbabilidadeMeta(kpi: KpiResponse) {
  const diasTotais = kpi.dias_decorridos + kpi.dias_restantes
  return kpi.indicadores
    .filter((i) => i.indicador === 'ola_quebrado')
    .map((i) => {
      const cor = STATUS_COR[i.status]
      const projecao = kpi.dias_decorridos > 0 ? (i.contagem_acumulada_ano / kpi.dias_decorridos) * diasTotais : i.contagem_acumulada_ano
      return {
        prio: i.bucket_prioridade,
        status: cor.label,
        statusColor: cor.fg,
        probabilidade: fmt1(i.probabilidade_atingir_meta_pct),
        calculo: `(${fmtNum(i.contagem_acumulada_ano)} ÷ ${kpi.dias_decorridos}) × ${diasTotais} = ${fmtNum(projecao)} quebras projetadas`,
      }
    })
}

// ---------------------------------------------------------------------------
// Fatores
// ---------------------------------------------------------------------------

export function computeImportanciaFeatures(itens: ImportanciaItem[]) {
  const max = Math.max(...itens.map((i) => i.importance_pct), 0.0001)
  return itens.map((it, i) => ({
    name: it.conceito ?? it.feature ?? '—',
    v: `${fmt2(it.importance_pct)}%`,
    w: `${((it.importance_pct / max) * 100).toFixed(1)}%`,
    fill: i < 3 ? BLUE : 'rgba(30,111,217,.35)',
  }))
}

/** Escolhe o incidente de maior score_calibrado e devolve suas contribuições SHAP. */
export function computeShapExplicacao(shapItems: ShapItem[]) {
  if (shapItems.length === 0) return { incidentId: null as string | null, score: null as number | null, rows: [] }
  const incidentId = shapItems.reduce((best, s) => (s.score_calibrado > best.score_calibrado ? s : best), shapItems[0]).incident_id
  const doIncidente = shapItems.filter((s) => s.incident_id === incidentId).sort((a, b) => a.rank_abs - b.rank_abs)
  const maxAbs = Math.max(...doIncidente.map((s) => Math.abs(s.shap_value)), 0.0001)
  const rows = doIncidente.map((s) => {
    const w = (Math.abs(s.shap_value) / maxAbs) * 50
    const positivo = s.direcao === 'aumenta_risco'
    return {
      name: s.feature,
      v: (positivo ? '+' : '−') + fmt2(Math.abs(s.shap_value)),
      fill: positivo ? RED : GREEN,
      left: positivo ? '50%' : `${(50 - w).toFixed(1)}%`,
      w: `${w.toFixed(1)}%`,
    }
  })
  return { incidentId, score: doIncidente[0]?.score_calibrado ?? null, rows }
}

export function computeHeatmap(celulas: HeatmapCelula[]) {
  const diasOrdenados = [...new Set(celulas.map((c) => c.dia_semana_num))].sort((a, b) => a - b)
  const nomesDia = new Map(celulas.map((c) => [c.dia_semana_num, c.nome_dia]))
  const dows = diasOrdenados.map((d) => nomesDia.get(d) ?? String(d))
  const maxVol = Math.max(...celulas.map((c) => c.volume_medio), 0.0001)

  const categorias = [...new Set(celulas.map((c) => c.categoria))]
  const porCategoria = new Map<string, Map<number, number>>()
  for (const c of celulas) {
    if (!porCategoria.has(c.categoria)) porCategoria.set(c.categoria, new Map())
    porCategoria.get(c.categoria)!.set(c.dia_semana_num, c.volume_medio)
  }
  const heat = categorias.map((cat) => ({
    cat,
    cells: diasOrdenados.map((d) => {
      const v = porCategoria.get(cat)?.get(d) ?? 0
      const a = v / maxVol
      return { v: fmt1(v), bg: `rgba(30,111,217,${(0.06 + a * 0.82).toFixed(3)})`, fg: a > 0.55 ? '#FFFFFF' : '#101C2E' }
    }),
  }))
  return { dows, heat }
}

// ---------------------------------------------------------------------------
// Clusters
// ---------------------------------------------------------------------------

export function computeBolhas(clusters: ClusterItem[]) {
  const BX0 = 60, BX1 = 880, BY0 = 16, BY1 = 316
  const durMax = Math.max(...clusters.map((c) => c.duracao_media_horas ?? 0), 1) * 1.1
  const violMax = Math.max(...clusters.map((c) => c.taxa_excedeu_tempo_esperado_pct ?? 0), 1) * 1.1
  const bubbles = clusters.map((c) => {
    const dur = c.duracao_media_horas ?? 0
    const viol = c.taxa_excedeu_tempo_esperado_pct ?? 0
    const cx = +(BX0 + (dur / durMax) * (BX1 - BX0)).toFixed(1)
    const cy = +(BY0 + (1 - viol / violMax) * (BY1 - BY0)).toFixed(1)
    const r = +(6 + Math.sqrt(c.pct_volume) * 4.5).toFixed(1)
    return {
      cx,
      cy,
      r,
      name: c.cluster_id,
      stroke: c.cor_hex,
      fill: `${c.cor_hex}2E`,
      ly: +(cy + 5).toFixed(1),
      sy: +(cy + r + 16).toFixed(1),
      meta: `${fmt1(dur)}h · ${fmt1(viol)}% · ${fmt1(c.pct_volume)}%`,
    }
  })

  // Clusters reais podem ficar próximos em duração/taxa (ex.: A e C) a ponto
  // de as bolhas se sobreporem — sem isso os rótulos ficam ilegíveis
  // (texto de um cluster em cima do outro). Escalona verticalmente os
  // rótulos de qualquer grupo cujos centros fiquem a menos que a soma dos
  // raios de distância; a sobreposição das bolhas em si é mantida (é o dado
  // real, não um artefato a esconder).
  const usados = new Set<number>()
  for (let i = 0; i < bubbles.length; i++) {
    if (usados.has(i)) continue
    const grupo = [i]
    for (let j = i + 1; j < bubbles.length; j++) {
      if (usados.has(j)) continue
      const dist = Math.hypot(bubbles[i].cx - bubbles[j].cx, bubbles[i].cy - bubbles[j].cy)
      if (dist < bubbles[i].r + bubbles[j].r) grupo.push(j)
    }
    if (grupo.length > 1) {
      grupo.sort((a, b) => bubbles[a].cx - bubbles[b].cx)
      grupo.forEach((idx, ordem) => {
        usados.add(idx)
        const b = bubbles[idx]
        b.ly = +(b.cy + 5 - (grupo.length - 1) * 7 + ordem * 14).toFixed(1)
        b.sy = +(Math.max(...grupo.map((k) => bubbles[k].cy + bubbles[k].r)) + 16 + ordem * 13).toFixed(1)
      })
    }
  }
  const bubGridY = [0, 0.25, 0.5, 0.75, 1].map((t) => {
    const v = t * violMax
    const y = +(BY0 + (1 - t) * (BY1 - BY0)).toFixed(1)
    return { y, ty: +(y + 3.5).toFixed(1), label: `${fmt1(v)}%` }
  })
  const bubGridX = [0, 0.2, 0.4, 0.6, 0.8, 1].map((t) => ({
    x: +(BX0 + t * (BX1 - BX0)).toFixed(1),
    label: `${fmt1(t * durMax)}h`,
  }))
  return { bubbles, bubGridY, bubGridX }
}

export function computeClustersCards(clusters: ClusterItem[]) {
  return clusters.map((c) => ({
    id: c.cluster_id,
    name: c.nome_perfil,
    tags: c.tags,
    read: c.descricao_curta,
    dur: c.duracao_media_horas !== null ? `${fmt1(c.duracao_media_horas)} h` : '—',
    viol: c.taxa_excedeu_tempo_esperado_pct !== null ? `${fmt1(c.taxa_excedeu_tempo_esperado_pct)}%` : '—',
    vol: `${fmt1(c.pct_volume)}%`,
    chipFg: c.cor_hex,
    chipBg: `${c.cor_hex}20`,
  }))
}

// ---------------------------------------------------------------------------
// Alertas
// ---------------------------------------------------------------------------

const SEVERIDADE_ALERTA: Record<Alerta['tipo'], { dot: string; bg: string; fg: string; label: string }> = {
  critico: { dot: RED, bg: 'rgba(214,69,69,.12)', fg: RED, label: 'alta' },
  atencao: { dot: AMBER_FILL, bg: 'rgba(232,163,23,.14)', fg: AMBER, label: 'média' },
  info: { dot: BLUE, bg: 'rgba(30,111,217,.12)', fg: BLUE, label: 'baixa' },
}

export function computeAlertas(alertas: Alerta[]) {
  return alertas.map((a) => {
    const s = SEVERIDADE_ALERTA[a.tipo]
    return { rule: a.regra_origem, sev: s.label, title: a.titulo, body: a.mensagem, dot: s.dot, badgeBg: s.bg, badgeFg: s.fg }
  })
}

const REGRA_ORIGEM_LABEL: Record<string, string> = {
  pico_volume_d1: 'Volume previsto para D+1',
  pressao_operacional_equipe: 'Pressão operacional por equipe',
  cluster_alta_violacao: 'Perfil operacional com tempo elevado',
  concentracao_categoria: 'Concentração de categoria',
  recorrencia_operacional: 'Recorrência operacional',
}

/** A API devolve um `texto` único por recomendação (sem título/corpo
 * separados) — o título vem de um rótulo humano fixo por `regra_origem`. */
export function computeRecomendacoes(recs: Recomendacao[]) {
  return recs.map((r) => ({
    n: String(r.ordem).padStart(2, '0'),
    title: REGRA_ORIGEM_LABEL[r.regra_origem] ?? r.regra_origem,
    body: r.texto,
    from: r.regra_origem,
  }))
}
