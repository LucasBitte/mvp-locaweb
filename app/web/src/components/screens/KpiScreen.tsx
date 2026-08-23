import { getKpi } from '../../lib/api'
import { useApi } from '../../lib/useApi'
import { computeBandasMeta, computeKpiResumo, computeProbabilidadeMeta } from '../../data/dashboardData'
import { MUTED, NAVY, SUB } from '../../lib/theme'
import { SourceTag } from '../SourceTag'
import { ErrorState, Loading } from '../ApiStatus'

const cardStyle = {
  background: '#FFFFFF',
  borderRadius: 16,
  padding: 24,
  boxShadow: '0 4px 16px rgba(10,22,40,.03)',
  display: 'flex',
  flexDirection: 'column' as const,
  gap: 12,
}
const kicker = { font: '600 12px/1 Inter,sans-serif', textTransform: 'uppercase' as const, letterSpacing: '.05em', color: SUB }
const cardTitle = { font: '600 20px/1.2 Manrope,sans-serif', color: NAVY }
const cardClass = 'transition-transform duration-200 hover:-translate-y-[3px]'

interface KpiScreenProps {
  mostrarOrigem: boolean
}

export function KpiScreen({ mostrarOrigem }: KpiScreenProps) {
  const { data, loading, error } = useApi(() => getKpi(), [])

  if (loading) return <Loading />
  if (error || !data) return <ErrorState error={error ?? 'sem dado'} />

  const bands = computeBandasMeta(data.indicadores)
  const resumo = computeKpiResumo(data)
  const probabilidades = computeProbabilidadeMeta(data)

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" style={{ gap: 20 }}>
        <div className={cardClass} style={cardStyle}>
          <span style={kicker}>Dias decorridos · {resumo.ano}</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>{resumo.diasDecorridos}</span>
            <span style={{ font: "500 15px/1 'JetBrains Mono',monospace", color: SUB }}>/ {resumo.diasTotais}</span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: '#F0F3FF', overflow: 'hidden' }}>
            <div style={{ width: `${(resumo.diasDecorridos / resumo.diasTotais) * 100}%`, height: '100%', background: '#1E6FD9' }} />
          </div>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>
            {resumo.diasRestantes} dias restantes · âncora temporal do pipeline, não a data real
          </span>
        </div>

        <div className={cardClass} style={cardStyle}>
          <span style={kicker}>OLA quebrados no ano</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>{resumo.totalQuebras}</span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>P2 + P3</span>
          </div>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>{resumo.quebrasPorPrioridade}</span>
          <SourceTag variant="historico" visible={mostrarOrigem}>HISTÓRICO · DW · kpi_status_int</SourceTag>
        </div>

        <div className={cardClass} style={cardStyle}>
          <span style={kicker}>Status geral</span>
          <span style={{ font: '700 32px/1 Manrope,sans-serif', letterSpacing: '-.02em', color: resumo.statusGeral.fg }}>
            {resumo.statusGeral.label}
          </span>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>Pior status entre as 4 combinações prioridade × indicador</span>
          <SourceTag visible={mostrarOrigem}>REGRA · FAIXA ANUAL</SourceTag>
        </div>

        <div className={cardClass} style={cardStyle}>
          <span style={kicker}>Probabilidade média — OLA quebrado</span>
          <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>{resumo.probabilidadeMedia}%</span>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>Média P2/P3 — projeção linear, não modelo estatístico</span>
          <SourceTag visible={mostrarOrigem}>PROJEÇÃO LINEAR</SourceTag>
        </div>
      </div>

      <div className={cardClass} style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={cardTitle}>Meta anual por prioridade × indicador</span>
            <span style={{ font: '400 12px/1.4 Inter,sans-serif', color: SUB }}>
              Seis faixas contíguas de <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>ref_meta_sla_anual</span> — só existe
              meta para P2/P3, <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>pct_atingimento</span> 150/125/100/75/50/0%
            </span>
          </div>
          <SourceTag visible={mostrarOrigem}>REGRA · TABELA DE REFERÊNCIA</SourceTag>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {bands.map((b) => (
            <div key={b.key} className="grid grid-cols-1 sm:grid-cols-[190px_1fr]" style={{ gap: 20, alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <span style={{ font: "700 14px/1.3 'JetBrains Mono',monospace", color: NAVY }}>
                  {b.prio} · {b.indicadorLabel}
                </span>
                <span style={{ font: '400 11px/1.3 Inter,sans-serif', color: SUB }}>
                  acumulado <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 500, color: NAVY }}>{b.cur}</span>
                </span>
                <span
                  style={{
                    alignSelf: 'flex-start',
                    padding: '4px 9px',
                    borderRadius: 999,
                    background: b.badgeBg,
                    font: "500 11px/1.2 'JetBrains Mono',monospace",
                    color: b.badgeFg,
                  }}
                >
                  atingimento {b.att}
                </span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-6" style={{ gap: 5 }}>
                {b.cells.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      borderRadius: 10,
                      padding: '10px 8px 9px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                      background: c.bg,
                      outline: c.ring,
                      outlineOffset: 2,
                    }}
                  >
                    <span style={{ font: "500 10px/1 'JetBrains Mono',monospace", letterSpacing: '.04em', color: SUB }}>{c.att}</span>
                    <span style={{ font: "500 12px/1.2 'JetBrains Mono',monospace", color: NAVY }}>{c.range}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2" style={{ gap: 20 }}>
        {probabilidades.map((p) => (
          <div
            key={p.prio}
            className={cardClass}
            style={{
              background: '#F0F3FF',
              borderRadius: 16,
              padding: '24px 26px',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <span style={kicker}>Probabilidade de ficar dentro da meta anual — {p.prio}</span>
            <span style={{ font: '700 30px/1 Manrope,sans-serif', letterSpacing: '-.02em', color: p.statusColor }}>{p.status}</span>
            <span style={{ font: "600 22px/1 'JetBrains Mono',monospace", color: NAVY }}>{p.probabilidade}%</span>
            <div style={{ background: '#FFFFFF', borderRadius: 12, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ font: "500 12px/1.6 'JetBrains Mono',monospace", color: MUTED }}>{p.calculo}</span>
            </div>
            <SourceTag visible={mostrarOrigem}>PROJEÇÃO LINEAR — NÃO É MODELO ESTATÍSTICO</SourceTag>
          </div>
        ))}
      </div>
    </section>
  )
}
