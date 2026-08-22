import {
  computeMixHistorico,
  computePrioridadeFiltro,
  computeRecorrencia,
  computeTopCategorias,
  computeTopProdutos,
} from '../../data/dashboardData'
import { MUTED, NAVY, SUB } from '../../lib/theme'
import { SourceTag } from '../SourceTag'

const cardStyle = {
  background: '#FFFFFF',
  borderRadius: 16,
  padding: 24,
  boxShadow: '0 4px 16px rgba(10,22,40,.03)',
  display: 'flex',
  flexDirection: 'column' as const,
  gap: 16,
}
const cardTitle = { font: '600 20px/1.2 Manrope,sans-serif', color: NAVY }

interface DetalheScreenProps {
  mostrarOrigem: boolean
}

export function DetalheScreen({ mostrarOrigem }: DetalheScreenProps) {
  const prios = computePrioridadeFiltro()
  const mix = computeMixHistorico()
  const cats = computeTopCategorias()
  const prods = computeTopProdutos()
  const recur = computeRecorrencia()

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ background: '#F0F3FF', borderRadius: 16, padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={{ font: '600 12px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.05em', color: SUB }}>
            Foco padrão da tela
          </span>
          <span style={{ font: '600 17px/1.3 Manrope,sans-serif', color: NAVY }}>
            P2 + P3 — 78,9% do volume total{' '}
            <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 500, fontSize: 14, color: MUTED }}>(32.677 / 41.441)</span>
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ font: '600 10px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.08em', color: SUB }}>
            Filtro de prioridade
          </span>
          {prios.map((p) => (
            <button
              key={p.label}
              style={{
                appearance: 'none',
                cursor: 'pointer',
                border: 0,
                padding: '8px 14px',
                borderRadius: 12,
                font: "600 12px/1 'JetBrains Mono',monospace",
                background: p.bg,
                color: p.fg,
                boxShadow: p.shadow,
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 20 }}>
        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ font: "700 15px/1 'JetBrains Mono',monospace", color: NAVY }}>P2</span>
            <span style={{ padding: '5px 10px', borderRadius: 999, background: '#E6ECFB', font: "500 11px/1 'JetBrains Mono',monospace", color: '#1E6FD9' }}>
              SLA 4h
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 38px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>46,1</span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>previstos amanhã</span>
          </div>
          <div style={{ height: 1, background: 'rgba(10,22,40,.08)' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ font: '600 11px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.06em', color: SUB }}>
                % do limite mensal
              </span>
              <span style={{ font: "500 15px/1 'JetBrains Mono',monospace", color: '#8a6210' }}>62%</span>
            </div>
            <div style={{ height: 8, borderRadius: 4, background: '#F0F3FF', overflow: 'hidden' }}>
              <div style={{ width: '62%', height: '100%', background: '#E8A317' }} />
            </div>
            <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>
              Derivado da posição na faixa anual de <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>ref_meta_sla_anual</span> — não existe meta mensal própria.
            </span>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · fct_previsao_prioridade</SourceTag>
            <SourceTag visible={mostrarOrigem}>REGRA · limite</SourceTag>
          </div>
        </div>

        <div style={cardStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ font: "700 15px/1 'JetBrains Mono',monospace", color: NAVY }}>P3</span>
            <span style={{ padding: '5px 10px', borderRadius: 999, background: '#E6ECFB', font: "500 11px/1 'JetBrains Mono',monospace", color: '#1E6FD9' }}>
              SLA 12h
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 38px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>71,8</span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>previstos amanhã</span>
          </div>
          <div style={{ height: 1, background: 'rgba(10,22,40,.08)' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ font: '600 11px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.06em', color: SUB }}>
                % do limite mensal
              </span>
              <span style={{ font: "500 15px/1 'JetBrains Mono',monospace", color: '#0F9D58' }}>48%</span>
            </div>
            <div style={{ height: 8, borderRadius: 4, background: '#F0F3FF', overflow: 'hidden' }}>
              <div style={{ width: '48%', height: '100%', background: '#0F9D58' }} />
            </div>
            <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>Threshold oficial de P3 é 12h — não 24h.</span>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · fct_previsao_prioridade</SourceTag>
          </div>
        </div>

        <div style={{ ...cardStyle, gap: 14 }}>
          <span style={{ font: '600 12px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.05em', color: SUB }}>
            Composição do volume histórico
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
            {mix.map((m) => (
              <div key={m.p} style={{ display: 'grid', gridTemplateColumns: '34px 1fr 74px 58px', alignItems: 'center', gap: 12 }}>
                <span style={{ font: "600 12px/1 'JetBrains Mono',monospace", color: NAVY }}>{m.p}</span>
                <div style={{ height: 10, borderRadius: 5, background: '#F0F3FF', overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 5, background: m.fill, width: m.w }} />
                </div>
                <span style={{ font: "500 12px/1 'JetBrains Mono',monospace", textAlign: 'right', color: MUTED }}>{m.n}</span>
                <span style={{ font: "500 12px/1 'JetBrains Mono',monospace", textAlign: 'right', color: NAVY }}>{m.pct}</span>
              </div>
            ))}
          </div>
          <span style={{ font: '400 11px/1.45 Inter,sans-serif', color: SUB }}>
            Outras prioridades permanecem acessíveis pelo filtro — nenhuma faixa é ocultada.
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 20 }}>
        <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
            <span style={cardTitle}>Top 5 categorias — volume previsto D+1</span>
            <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO</SourceTag>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {cats.map((c) => (
              <div key={c.name} style={{ display: 'grid', gridTemplateColumns: '76px 1fr 56px', alignItems: 'center', gap: 14 }}>
                <span style={{ font: "500 13px/1 'JetBrains Mono',monospace", color: NAVY }}>{c.name}</span>
                <div style={{ height: 12, borderRadius: 6, background: '#F0F3FF', overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 6, background: '#1E6FD9', width: c.w }} />
                </div>
                <span style={{ font: "500 13px/1 'JetBrains Mono',monospace", textAlign: 'right', color: MUTED }}>{c.v}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
            <span style={cardTitle}>Top produtos — volume previsto D+1</span>
            <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO</SourceTag>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {prods.map((p) => (
              <div key={p.name} style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={{ font: "500 14px/1 'JetBrains Mono',monospace", color: NAVY }}>{p.name}</span>
                  <span style={{ font: '400 12px/1 Inter,sans-serif', color: SUB }}>
                    {p.share} do histórico ·{' '}
                    <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 500, color: NAVY }}>{p.pred}</span> previstos
                  </span>
                </div>
                <div style={{ height: 10, borderRadius: 5, background: '#F0F3FF', overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 5, background: '#1E6FD9', width: p.w }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={cardTitle}>Recorrência operacional</span>
            <span style={{ font: '400 12px/1.4 Inter,sans-serif', color: SUB }}>Últimos 30 dias comparados aos 30 dias anteriores</span>
          </div>
          <SourceTag visible={mostrarOrigem}>REGRA · JANELA MÓVEL</SourceTag>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 16, marginTop: 16 }}>
          {recur.map((r) => (
            <div key={r.name} style={{ background: '#F9F9FF', borderRadius: 12, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ font: "600 15px/1 'JetBrains Mono',monospace", color: NAVY }}>{r.name}</span>
                <span style={{ padding: '4px 10px', borderRadius: 999, background: r.badgeBg, font: '500 11px/1.2 Inter,sans-serif', color: r.badgeFg }}>
                  {r.badge}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <span style={{ font: "600 26px/1 'JetBrains Mono',monospace", color: r.badgeFg }}>{r.delta}</span>
                <span style={{ font: '400 12px/1.3 Inter,sans-serif', color: SUB }}>vs. janela anterior</span>
              </div>
              <span style={{ font: '400 12px/1.5 Inter,sans-serif', color: MUTED }}>
                Presente em <span style={{ fontFamily: "'JetBrains Mono',monospace", fontWeight: 500, color: NAVY }}>{r.days}</span> dos dias da janela — {r.note}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
