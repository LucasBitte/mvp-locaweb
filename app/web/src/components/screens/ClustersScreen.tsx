import { computeBolhas, computeClustersCards } from '../../data/dashboardData'
import { MUTED, NAVY, SUB } from '../../lib/theme'
import { SourceTag } from '../SourceTag'

interface ClustersScreenProps {
  mostrarOrigem: boolean
}

export function ClustersScreen({ mostrarOrigem }: ClustersScreenProps) {
  const { bubbles, bubGridX, bubGridY } = computeBolhas()
  const clusters = computeClustersCards()

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ font: '600 20px/1.2 Manrope,sans-serif', color: NAVY }}>Perfis operacionais — duração × violação × volume</span>
            <span style={{ font: '400 12px/1.4 Inter,sans-serif', color: SUB }}>
              Eixo X duração média (h) · eixo Y taxa de violação de OLA (%) · área da bolha = % do volume total
            </span>
          </div>
          <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · K-MEANS</SourceTag>
        </div>
        <svg viewBox="0 0 900 360" style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
          {bubGridY.map((g, i) => (
            <line key={i} x1={60} x2={880} y1={g.y} y2={g.y} stroke="rgba(10,22,40,.07)" strokeWidth={1} />
          ))}
          {bubGridX.map((g, i) => (
            <line key={i} x1={g.x} x2={g.x} y1={16} y2={316} stroke="rgba(10,22,40,.04)" strokeWidth={1} />
          ))}
          <text x={470} y={356} textAnchor="middle" fontFamily="Inter, sans-serif" fontSize={11} fill={SUB}>
            duração média (horas)
          </text>
          {bubbles.map((b) => (
            <circle key={b.name} cx={b.cx} cy={b.cy} r={b.r} fill={b.fill} stroke={b.stroke} strokeWidth={1.5} />
          ))}
          {bubGridY.map((g, i) => (
            <text key={`by${i}`} x={50} y={g.ty} textAnchor="end" fontFamily="JetBrains Mono, monospace" fontSize={10} fill={SUB}>
              {g.label}
            </text>
          ))}
          {bubGridX.map((g, i) => (
            <text key={`bx${i}`} x={g.x} y={336} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize={10} fill={SUB}>
              {g.label}
            </text>
          ))}
          {bubbles.map((b) => (
            <text key={`bn${b.name}`} x={b.cx} y={b.ly} textAnchor="middle" fontFamily="Manrope, sans-serif" fontSize={15} fontWeight={700} fill={b.stroke}>
              {b.name}
            </text>
          ))}
          {bubbles.map((b) => (
            <text key={`bm${b.name}`} x={b.cx} y={b.sy} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize={10} fill={MUTED}>
              {b.meta}
            </text>
          ))}
        </svg>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 20 }}>
        {clusters.map((c) => (
          <div key={c.id} style={{ background: '#FFFFFF', borderRadius: 16, padding: 22, boxShadow: '0 4px 16px rgba(10,22,40,.03)', display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: 9,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  font: '700 14px/1 Manrope,sans-serif',
                  background: c.chipBg,
                  color: c.chipFg,
                }}
              >
                {c.id}
              </span>
              <span style={{ font: '600 15px/1.25 Manrope,sans-serif', color: NAVY }}>{c.name}</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {c.tags.map((t) => (
                <span key={t} style={{ padding: '4px 9px', borderRadius: 999, background: '#F0F3FF', font: '500 10px/1.2 Inter,sans-serif', letterSpacing: '.02em', color: MUTED }}>
                  {t}
                </span>
              ))}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ font: '400 11px/1 Inter,sans-serif', color: SUB }}>Duração média</span>
                <span style={{ font: "500 12px/1 'JetBrains Mono',monospace", color: NAVY }}>{c.dur}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ font: '400 11px/1 Inter,sans-serif', color: SUB }}>Violação de OLA</span>
                <span style={{ font: "500 12px/1 'JetBrains Mono',monospace", color: c.chipFg }}>{c.viol}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ font: '400 11px/1 Inter,sans-serif', color: SUB }}>% do volume</span>
                <span style={{ font: "500 12px/1 'JetBrains Mono',monospace", color: NAVY }}>{c.vol}</span>
              </div>
            </div>
            <div style={{ height: 1, background: 'rgba(10,22,40,.08)' }} />
            <p style={{ font: '400 12px/1.55 Inter,sans-serif', color: MUTED, textWrap: 'pretty' }}>{c.read}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
