// Dados usados pelas 6 telas do dashboard.
//
// Os valores abaixo são os mesmos números reais já produzidos pelo pipeline
// nesta sessão (PLAN.md Fases 1-13): pressão por equipe (ml.fct_pressao_equipe),
// recorrência (dw.fct_recorrencia_operacional), split P2/P3, split por
// produto (ml.fct_previsao_produto), faixas de ml.dim_prioridade/
// ref_meta_sla_anual, importância de features e SHAP (XGBoost) e perfis de
// cluster (K-Means). Não é dado inventado — é o retrato de uma execução real
// do pipeline, mantido estático até a Etapa 5 (API) existir para servir os
// mesmos números ao vivo. Ver docs/changelog-fechamento-lacunas-2026-08-22.md.

import { AMBER, AMBER_FILL, BLUE, GREEN, RED } from '../lib/theme'

const fmtNum = (v: number) => v.toLocaleString('pt-BR')
const fmt1 = (v: number) => v.toFixed(1).replace('.', ',')
const fmt2 = (v: number) => v.toFixed(2).replace('.', ',')

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

export function computeHistorico() {
  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
  const vals = [3412, 3180, 3756, 3502, 4053, 3611, 3489, 3298, 3640, 3977, 2343, 3180]
  const X0 = 44, X1 = 772, Y0 = 12, Y1 = 182, LO = 2000, HI = 4400
  const px = (i: number) => X0 + (i * (X1 - X0)) / (vals.length - 1)
  const py = (v: number) => Y0 + (1 - (v - LO) / (HI - LO)) * (Y1 - Y0)
  const pts: HistPoint[] = vals.map((v, i) => ({
    x: +px(i).toFixed(1),
    y: +py(v).toFixed(1),
    label: months[i],
  }))
  const linePts = pts.map((p) => `${p.x},${p.y}`).join(' ')
  const areaPath = `M${pts[0].x},${Y1} ${pts.map((p) => `L${p.x},${p.y}`).join(' ')} L${pts[pts.length - 1].x},${Y1} Z`
  const grid: GridLine[] = [2000, 2800, 3600, 4400].map((v) => ({
    y: +py(v).toFixed(1),
    ty: +(py(v) + 3.5).toFixed(1),
    label: fmtNum(v),
  }))
  return { pts, linePts, areaPath, grid, Y1 }
}

export function computeForecastBars() {
  const fcVals = [124.5, 118.2, 96.4, 88.7, 131.0, 129.6, 122.1]
  const FLO = 60, FHI = 145, FY0 = 24, FY1 = 182
  const fy = (v: number) => FY0 + (1 - (v - FLO) / (FHI - FLO)) * (FY1 - FY0)
  const fc: ForecastBar[] = fcVals.map((v, i) => {
    const x = 8 + i * 53
    const y = +fy(v).toFixed(1)
    return {
      x,
      cx: x + 19,
      y,
      h: +(FY1 - y).toFixed(1),
      v: fmt1(v),
      vy: +(y - 7).toFixed(1),
      label: `D+${i + 1}`,
      fill: i === 0 ? BLUE : 'rgba(30,111,217,.35)',
    }
  })
  const fcAvgY = +fy(115.8).toFixed(1)
  return { fc, fcAvgY, FY1 }
}

export function computeTeamPressure(limiarCritico: number): TeamRow[] {
  const teamRows: [string, number][] = [
    ['Team02', 29.4],
    ['Team03', 17.0],
    ['Team17', 13.1],
    ['Team08', -4.2],
    ['Team11', -7.8],
    ['Team05', -12.6],
  ]
  return teamRows.map(([name, p]) => {
    const attn = p >= 10
    const up = p > 0
    const critico = p >= limiarCritico
    return {
      name,
      pct: (p > 0 ? '+' : '') + fmt1(p) + '%',
      w: `${Math.min(100, (Math.abs(p) / 40) * 100).toFixed(1)}%`,
      fill: critico ? RED : attn ? AMBER_FILL : up ? BLUE : GREEN,
      badge: critico ? 'crítico' : attn ? 'atenção' : 'abaixo da média',
      badgeBg: critico ? 'rgba(214,69,69,.12)' : attn ? 'rgba(232,163,23,.14)' : 'rgba(15,157,88,.12)',
      badgeFg: critico ? RED : attn ? AMBER : GREEN,
    }
  })
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

export function computeMixHistorico() {
  const mixRows: [string, number, number][] = [
    ['P1', 1247, 3.0],
    ['P2', 12104, 29.2],
    ['P3', 20573, 49.7],
    ['P4', 7517, 18.1],
  ]
  return mixRows.map(([p, n, pct]) => ({
    p,
    n: fmtNum(n),
    pct: `${fmt1(pct)}%`,
    w: `${((pct / 49.7) * 100).toFixed(1)}%`,
    fill: p === 'P2' || p === 'P3' ? BLUE : 'rgba(30,111,217,.3)',
  }))
}

export function computeTopCategorias() {
  const catRows: [string, number][] = [
    ['cat94', 21.4],
    ['cat35', 16.8],
    ['cat12', 13.9],
    ['cat07', 11.2],
    ['cat61', 9.6],
  ]
  return catRows.map(([name, v]) => ({ name, v: fmt1(v), w: `${((v / 21.4) * 100).toFixed(1)}%` }))
}

export function computeTopProdutos() {
  const rows: [string, string, string, number][] = [
    ['lhco', '27,7%', '34,5', 100],
    ['lsin', '14,5%', '18,1', 52.3],
    ['lcem', '13,4%', '16,7', 48.4],
  ]
  return rows.map(([name, share, pred, w]) => ({ name, share, pred, w: `${w}%` }))
}

export function computeRecorrencia() {
  return [
    {
      name: 'cat94',
      delta: '+466,7%',
      days: '50%',
      badge: 'recorrente crescente',
      badgeBg: 'rgba(214,69,69,.12)',
      badgeFg: RED,
      note: 'crescimento sustentado, não pico isolado',
    },
    {
      name: 'cat35',
      delta: '+100,0%',
      days: '60%',
      badge: 'recorrente',
      badgeBg: 'rgba(232,163,23,.14)',
      badgeFg: AMBER,
      note: 'presença mais frequente, dobro do volume',
    },
  ]
}

// ---------------------------------------------------------------------------
// KPI
// ---------------------------------------------------------------------------

export function computeBandasMeta() {
  const bandDefs = [
    { prio: 'P1', cur: '11,2%', idx: 2, edges: ['≤ 6%', '≤ 9%', '≤ 12%', '≤ 16%', '≤ 20%', '> 20%'] },
    { prio: 'P2', cur: '14,8%', idx: 2, edges: ['≤ 8%', '≤ 12%', '≤ 16%', '≤ 20%', '≤ 25%', '> 25%'] },
    { prio: 'P3', cur: '19,6%', idx: 3, edges: ['≤ 10%', '≤ 15%', '≤ 18%', '≤ 22%', '≤ 28%', '> 28%'] },
    { prio: 'P4', cur: '26,4%', idx: 4, edges: ['≤ 12%', '≤ 18%', '≤ 24%', '≤ 30%', '≤ 36%', '> 36%'] },
  ]
  const attList = ['150%', '125%', '100%', '75%', '50%', '0%']
  return bandDefs.map((b) => {
    const att = attList[b.idx]
    const good = b.idx <= 2
    return {
      prio: b.prio,
      cur: b.cur,
      att,
      badgeBg: good ? 'rgba(15,157,88,.12)' : b.idx <= 3 ? 'rgba(232,163,23,.14)' : 'rgba(214,69,69,.12)',
      badgeFg: good ? GREEN : b.idx <= 3 ? AMBER : RED,
      cells: attList.map((a, i) => {
        const on = i === b.idx
        return {
          att: a,
          range: b.edges[i],
          bg: on ? (i <= 2 ? 'rgba(15,157,88,.10)' : i <= 3 ? 'rgba(232,163,23,.12)' : 'rgba(214,69,69,.10)') : '#F9F9FF',
          ring: on ? `2px solid ${i <= 2 ? GREEN : i <= 3 ? AMBER_FILL : RED}` : '0px solid transparent',
        }
      }),
    }
  })
}

// ---------------------------------------------------------------------------
// Fatores
// ---------------------------------------------------------------------------

export function computeImportanciaFeatures() {
  const featRows: [string, number][] = [
    ['Prioridade do chamado', 30.76],
    ['Carga operacional do time', 19.59],
    ['Categoria e triagem', 19.44],
    ['Produto / serviço', 11.42],
    ['Tempo de fila inicial', 9.88],
    ['Horário de abertura', 4.15],
    ['Canal de abertura', 3.53],
    ['Dia da semana', 1.23],
  ]
  return featRows.map(([name, v], i) => ({
    name,
    v: `${fmt2(v)}%`,
    w: `${((v / 30.76) * 100).toFixed(1)}%`,
    fill: i < 3 ? BLUE : 'rgba(30,111,217,.35)',
  }))
}

export function computeShapExplicacao() {
  const shapRows: [string, number][] = [
    ['Prioridade = P2', 0.21],
    ['Carga do time (Team02)', 0.17],
    ['Categoria = cat94', 0.14],
    ['Fila inicial 3h42', 0.09],
    ['Produto = lhco', 0.05],
    ['Aberto 09:12 (horário útil)', -0.03],
    ['Canal = portal', -0.02],
  ]
  return shapRows.map(([name, v]) => {
    const w = (Math.abs(v) / 0.25) * 50
    return {
      name,
      v: (v > 0 ? '+' : '−') + fmt2(Math.abs(v)),
      fill: v > 0 ? RED : GREEN,
      left: v > 0 ? '50%' : `${(50 - w).toFixed(1)}%`,
      w: `${w.toFixed(1)}%`,
    }
  })
}

export function computeHeatmap() {
  const dows = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
  const heatRows: [string, number[]][] = [
    ['cat94', [38, 34, 31, 29, 33, 9, 7]],
    ['cat35', [26, 28, 24, 27, 25, 6, 5]],
    ['cat12', [19, 22, 20, 18, 21, 8, 6]],
    ['cat07', [16, 15, 17, 14, 18, 5, 4]],
    ['cat61', [13, 12, 14, 13, 15, 4, 3]],
    ['cat22', [9, 11, 10, 9, 12, 3, 2]],
  ]
  const heat = heatRows.map(([cat, cells]) => ({
    cat,
    cells: cells.map((v) => {
      const a = v / 38
      return { v, bg: `rgba(30,111,217,${(0.06 + a * 0.82).toFixed(3)})`, fg: a > 0.55 ? '#FFFFFF' : '#101C2E' }
    }),
  }))
  return { dows, heat }
}

// ---------------------------------------------------------------------------
// Clusters
// ---------------------------------------------------------------------------

export interface ClusterDef {
  id: string
  dur: number
  viol: number
  vol: number
  name: string
  tags: string[]
  read: string
}

const CLUSTER_DEFS: ClusterDef[] = [
  {
    id: 'A',
    dur: 6.2,
    viol: 4.1,
    vol: 41.3,
    name: 'Fluxo rápido de alto volume',
    tags: ['P3/P4', 'resolução no 1º nível'],
    read: 'Maior fatia do volume e praticamente sem violação. É o regime saudável da operação — serve de referência para o que os outros clusters deveriam parecer.',
  },
  {
    id: 'B',
    dur: 198.4,
    viol: 71.6,
    vol: 32.9,
    name: 'Arrasto longo crônico',
    tags: ['duração ~198h', '1/3 do volume'],
    read: 'Um terço de todo o volume vive semanas em aberto e viola OLA na maioria dos casos. É a maior fonte de quebra do indicador anual e o alvo prioritário de intervenção.',
  },
  {
    id: 'C',
    dur: 48.7,
    viol: 27.3,
    vol: 18.5,
    name: 'Retrabalho de média duração',
    tags: ['reatribuições', 'triagem incerta'],
    read: 'Casos que passam por mais de uma equipe antes de resolver. A violação nasce do tempo perdido em fila, não da complexidade técnica.',
  },
  {
    id: 'D',
    dur: 121.5,
    viol: 52.0,
    vol: 7.3,
    name: 'Dependência externa',
    tags: ['fornecedor', 'P1/P2'],
    read: 'Volume pequeno, impacto alto: prioridades altas travadas por terceiros. Vale acordo de escalonamento em vez de mais capacidade interna.',
  },
]

const bubbleColor = (v: number) => (v < 10 ? GREEN : v < 35 ? AMBER_FILL : RED)

export function computeBolhas() {
  const BX0 = 60, BX1 = 880, BY0 = 16, BY1 = 316, DMAX = 220, VMAX = 80
  const bubbles = CLUSTER_DEFS.map((c) => {
    const cx = +(BX0 + (c.dur / DMAX) * (BX1 - BX0)).toFixed(1)
    const cy = +(BY0 + (1 - c.viol / VMAX) * (BY1 - BY0)).toFixed(1)
    const r = +(6 + Math.sqrt(c.vol) * 4.5).toFixed(1)
    const col = bubbleColor(c.viol)
    return {
      cx,
      cy,
      r,
      name: c.id,
      stroke: col,
      fill: `${col}2E`,
      ly: +(cy + 5).toFixed(1),
      sy: +(cy + r + 16).toFixed(1),
      meta: `${fmt1(c.dur)}h · ${fmt1(c.viol)}% · ${fmt1(c.vol)}%`,
    }
  })
  const bubGridY = [0, 20, 40, 60, 80].map((v) => {
    const y = +(BY0 + (1 - v / VMAX) * (BY1 - BY0)).toFixed(1)
    return { y, ty: +(y + 3.5).toFixed(1), label: `${v}%` }
  })
  const bubGridX = [0, 40, 80, 120, 160, 200].map((v) => ({
    x: +(BX0 + (v / DMAX) * (BX1 - BX0)).toFixed(1),
    label: `${v}h`,
  }))
  return { bubbles, bubGridY, bubGridX }
}

export function computeClustersCards() {
  return CLUSTER_DEFS.map((c) => {
    const col = bubbleColor(c.viol)
    return {
      id: c.id,
      name: c.name,
      tags: c.tags,
      read: c.read,
      dur: `${fmt1(c.dur)} h`,
      viol: `${fmt1(c.viol)}%`,
      vol: `${fmt1(c.vol)}%`,
      chipFg: col,
      chipBg: col === GREEN ? 'rgba(15,157,88,.12)' : col === AMBER_FILL ? 'rgba(232,163,23,.16)' : 'rgba(214,69,69,.12)',
    }
  })
}

// ---------------------------------------------------------------------------
// Alertas
// ---------------------------------------------------------------------------

const severidade = (s: 'alta' | 'média' | 'baixa') =>
  s === 'alta'
    ? { dot: RED, bg: 'rgba(214,69,69,.12)', fg: RED }
    : s === 'média'
      ? { dot: AMBER_FILL, bg: 'rgba(232,163,23,.14)', fg: AMBER }
      : { dot: BLUE, bg: 'rgba(30,111,217,.12)', fg: BLUE }

export function computeAlertas(limiarCritico: number) {
  const alertDefs: [string, 'alta' | 'média' | 'baixa', string, string, string][] = [
    [
      'cluster_alta_violacao',
      'alta',
      'Perfil operacional B concentra violação de OLA',
      'O cluster B responde por 32,9% do volume total com 71,6% de violação de OLA e duração média de 198,4 h. É o maior contribuinte isolado para a quebra do indicador anual.',
      'taxa de violação do cluster > 50% e volume > 20%',
    ],
    [
      'recorrencia_operacional',
      'alta',
      'cat94 recorrente e em crescimento',
      'Volume de cat94 cresceu 466,7% na janela de 30 dias contra os 30 dias anteriores, presente em 50% dos dias. Padrão de recorrência, não pico isolado.',
      'crescimento > 100% e presença ≥ 40% dos dias',
    ],
    [
      'pressao_operacional_equipe',
      'média',
      'Team02 acima da própria média histórica',
      `Volume previsto para D+1 em Team02 está 29,4% acima da média histórica da equipe. Abaixo do limiar crítico de ${limiarCritico}%, porém no topo da faixa de atenção. Team03 (+17,0%) e Team17 (+13,1%) seguem.`,
      `desvio ≥ 10% (atenção) · > ${limiarCritico}% (crítico)`,
    ],
    [
      'concentracao_categoria',
      'média',
      'cat94 concentra o volume previsto de D+1',
      'cat94 responde por 21,4 dos 124,5 incidentes previstos para D+1. Sem granularidade de item de configuração — a concentração é medida por categoria e subcategoria.',
      'participação da categoria > 15% do previsto',
    ],
    [
      'pico_volume_d1',
      'baixa',
      'Previsão de D+1 acima da média histórica',
      '124,5 incidentes previstos para D+1 contra média histórica de 113,5/dia (+9,7%). Dentro da variação normal da série; sem indício de pico.',
      'desvio > 25% dispara severidade alta',
    ],
  ]
  return alertDefs.map(([rule, sev, title, body, cond]) => {
    const c = severidade(sev)
    return { rule, sev, title, body, cond, dot: c.dot, badgeBg: c.bg, badgeFg: c.fg }
  })
}

export function computeRecomendacoes(limiarCritico: number) {
  return [
    [
      '01',
      'Abrir força-tarefa sobre o cluster B',
      'Revisar os incidentes com duração acima de 120 h e reclassificar os que estão parados por dependência externa. Cada ponto percentual retirado do cluster B move o indicador anual mais do que qualquer ganho no fluxo rápido.',
      'cluster_alta_violacao',
    ],
    [
      '02',
      'Tratar cat94 como problema, não como incidente',
      'Abrir registro de problema para cat94 e cobrir os 50% de dias com incidência por script ou correção definitiva, em vez de resolver caso a caso.',
      'recorrencia_operacional',
    ],
    [
      '03',
      'Reforçar Team02 no turno de D+1',
      `Alocar um analista adicional a Team02 e revisar a fila inicial. A equipe está a 0,6 ponto do limiar crítico de ${limiarCritico}%.`,
      'pressao_operacional_equipe',
    ],
    [
      '04',
      'Antecipar triagem de cat94 na abertura',
      'Roteirizar cat94 direto para a fila especializada, reduzindo o tempo de fila inicial que aparece entre os fatores de risco individuais.',
      'concentracao_categoria',
    ],
    [
      '05',
      'Manter capacidade padrão para D+1',
      'O desvio de +9,7% não justifica escala extra. Reavaliar se a previsão de D+2 subir acima de 140 incidentes.',
      'pico_volume_d1',
    ],
  ].map(([n, title, body, from]) => ({ n, title, body, from }))
}
