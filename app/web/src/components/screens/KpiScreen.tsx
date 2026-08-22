import { computeBandasMeta } from '../../data/dashboardData'
import { MUTED, NAVY, SUB } from '../../lib/theme'
import { SourceTag } from '../SourceTag'

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

interface KpiScreenProps {
  mostrarOrigem: boolean
}

export function KpiScreen({ mostrarOrigem }: KpiScreenProps) {
  const bands = computeBandasMeta()

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 20 }}>
        <div style={cardStyle}>
          <span style={kicker}>Dias decorridos · dezembro 2025</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>31</span>
            <span style={{ font: "500 15px/1 'JetBrains Mono',monospace", color: SUB }}>/ 31</span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: '#F0F3FF', overflow: 'hidden' }}>
            <div style={{ width: '100%', height: '100%', background: '#1E6FD9' }} />
          </div>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>0 dias restantes · contagem de calendário puro, sem modelo</span>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>OLA quebrados no mês</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>583</span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>de 3.180</span>
          </div>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>Contagem sobre base histórica 2025</span>
          <SourceTag variant="historico" visible={mostrarOrigem}>HISTÓRICO · DW</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>% OLA quebrado no mês</span>
          <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: '#8a6210' }}>18,3%</span>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>Calculado a partir da posição na faixa anual</span>
          <SourceTag visible={mostrarOrigem}>REGRA · FAIXA ANUAL</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>% volume tratado no mês</span>
          <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: '#0F9D58' }}>81,7%</span>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>Complemento do percentual quebrado na mesma faixa</span>
          <SourceTag visible={mostrarOrigem}>REGRA · FAIXA ANUAL</SourceTag>
        </div>
      </div>

      <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={cardTitle}>Meta anual de OLA por prioridade</span>
            <span style={{ font: '400 12px/1.4 Inter,sans-serif', color: SUB }}>
              Seis faixas contíguas de <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>ref_meta_sla_anual</span> ·{' '}
              <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>pct_atingimento</span> 150 / 125 / 100 / 75 / 50 / 0%
            </span>
          </div>
          <SourceTag visible={mostrarOrigem}>REGRA · TABELA DE REFERÊNCIA</SourceTag>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {bands.map((b) => (
            <div key={b.prio} style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: 20, alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <span style={{ font: "700 15px/1 'JetBrains Mono',monospace", color: NAVY }}>{b.prio}</span>
                <span style={{ font: '400 11px/1.3 Inter,sans-serif', color: SUB }}>
                  quebra atual <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 500, color: NAVY }}>{b.cur}</span>
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
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,minmax(0,1fr))', gap: 5 }}>
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

      <div style={{ background: '#F0F3FF', borderRadius: 16, padding: '26px 28px', display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1.25fr)', gap: 32, alignItems: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <span style={kicker}>Probabilidade de atingir a meta anual</span>
          <span style={{ font: '700 34px/1 Manrope,sans-serif', letterSpacing: '-.02em', color: '#0F9D58' }}>Dentro da meta</span>
          <span style={{ font: "500 14px/1.4 'JetBrains Mono',monospace", color: MUTED }}>projeção 7.624 · teto 8.288 · 92,0% do teto</span>
          <SourceTag visible={mostrarOrigem}>PROJEÇÃO LINEAR — NÃO É MODELO ESTATÍSTICO</SourceTag>
        </div>
        <div style={{ background: '#FFFFFF', borderRadius: 12, padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <span style={{ font: '600 11px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.06em', color: SUB }}>
            Como o número é calculado
          </span>
          <span style={{ font: "500 14px/1.7 'JetBrains Mono',monospace", color: NAVY }}>
            (quebras_ate_agora ÷ dias_decorridos) × dias_totais_do_ano
          </span>
          <span style={{ font: "500 13px/1.7 'JetBrains Mono',monospace", color: MUTED }}>(7.624 ÷ 365) × 365 = 7.624</span>
          <div style={{ height: 1, background: 'rgba(10,22,40,.08)' }} />
          <span style={{ font: '400 12px/1.5 Inter,sans-serif', color: MUTED }}>
            Extrapolação aritmética do ritmo observado. Não usa Poisson, não usa aprendizado de máquina e não produz intervalo de confiança.
          </span>
        </div>
      </div>
    </section>
  )
}
