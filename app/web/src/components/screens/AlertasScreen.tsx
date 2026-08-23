import { getAlertas } from '../../lib/api'
import { useApi } from '../../lib/useApi'
import { computeAlertas, computeRecomendacoes } from '../../data/dashboardData'
import { MUTED, NAVY, SUB } from '../../lib/theme'
import { SourceTag } from '../SourceTag'
import { ErrorState, Loading } from '../ApiStatus'

const cardClass = 'transition-transform duration-200 hover:-translate-y-[3px]'

interface AlertasScreenProps {
  mostrarOrigem: boolean
}

export function AlertasScreen({ mostrarOrigem }: AlertasScreenProps) {
  const { data, loading, error } = useApi(() => getAlertas(), [])

  if (loading) return <Loading />
  if (error || !data) return <ErrorState error={error ?? 'sem dado'} />

  const alerts = computeAlertas(data.alertas)
  const recs = computeRecomendacoes(data.recomendacoes)

  return (
    <section className="grid grid-cols-1 lg:grid-cols-[1.35fr_1fr]" style={{ gap: 20, alignItems: 'start' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <span style={{ font: '600 20px/1.2 Manrope,sans-serif', color: NAVY }}>Alertas ativos</span>
          <span style={{ font: '400 12px/1.4 Inter,sans-serif', color: SUB }}>Cada alerta é disparado por uma regra explícita, com origem visível</span>
        </div>
        {alerts.map((a, i) => (
          <div key={`${a.rule}-${i}`} className={cardClass} style={{ background: '#FFFFFF', borderRadius: 16, padding: '22px 24px', boxShadow: '0 4px 16px rgba(10,22,40,.03)', display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: 999, background: a.dot }} />
                <span style={{ font: '600 16px/1.25 Manrope,sans-serif', color: NAVY }}>{a.title}</span>
              </div>
              <span
                style={{
                  padding: '4px 10px',
                  borderRadius: 999,
                  font: '500 10px/1.2 Inter,sans-serif',
                  textTransform: 'uppercase',
                  letterSpacing: '.06em',
                  background: a.badgeBg,
                  color: a.badgeFg,
                }}
              >
                {a.sev}
              </span>
            </div>
            <p style={{ font: '400 13px/1.6 Inter,sans-serif', color: MUTED, textWrap: 'pretty' }}>{a.body}</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ font: '600 10px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.08em', color: SUB }}>Origem da regra</span>
              <span style={{ padding: '5px 10px', borderRadius: 999, background: 'rgba(10,22,40,.06)', font: "500 11px/1 'JetBrains Mono',monospace", color: NAVY }}>
                {a.rule}
              </span>
            </div>
          </div>
        ))}
        <div style={{ background: '#F0F3FF', borderRadius: 16, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <span style={{ font: '600 12px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.05em', color: SUB }}>Limitação declarada</span>
          <p style={{ font: '400 13px/1.6 Inter,sans-serif', color: MUTED }}>
            Não há granularidade de item de configuração (CI) — a dimensão não existe no <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>dw</span>. Onde a
            análise pediria CI, o alerta aproxima por categoria e subcategoria. Nenhum CI é simulado.
          </p>
        </div>
      </div>

      <div className={cardClass} style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 26px', boxShadow: '0 4px 16px rgba(10,22,40,.03)', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ font: '600 20px/1.2 Manrope,sans-serif', color: NAVY }}>Recomendações</span>
          <span style={{ font: '400 12px/1.5 Inter,sans-serif', color: SUB }}>
            Texto gerado por regra e template a partir dos alertas acima. Nenhuma recomendação vem de modelo de aprendizado de máquina.
          </span>
          <SourceTag visible={mostrarOrigem}>REGRA · TEMPLATE PRESCRITIVO</SourceTag>
        </div>
        <div style={{ height: 1, background: 'rgba(10,22,40,.08)' }} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {recs.map((r) => (
            <div key={r.n} style={{ display: 'grid', gridTemplateColumns: '26px 1fr', gap: 12, alignItems: 'start' }}>
              <span style={{ font: "500 13px/1.5 'JetBrains Mono',monospace", color: '#1E6FD9' }}>{r.n}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <span style={{ font: '600 13px/1.4 Inter,sans-serif', color: NAVY }}>{r.title}</span>
                <span style={{ font: '400 12px/1.6 Inter,sans-serif', color: MUTED, textWrap: 'pretty' }}>{r.body}</span>
                <span style={{ font: "500 10px/1.3 'JetBrains Mono',monospace", color: SUB }}>← {r.from}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
