import { computeForecastBars, computeHistorico, computeTeamPressure } from '../../data/dashboardData'
import { MUTED, NAVY, SUB } from '../../lib/theme'
import { SourceTag } from '../SourceTag'

const cardStyle = {
  background: '#FFFFFF',
  borderRadius: 16,
  padding: 24,
  boxShadow: '0 4px 16px rgba(10,22,40,.03)',
  display: 'flex',
  flexDirection: 'column' as const,
  gap: 14,
}

const kicker = { font: '600 12px/1 Inter,sans-serif', textTransform: 'uppercase' as const, letterSpacing: '.05em', color: SUB }
const cardTitle = { font: '600 20px/1.2 Manrope,sans-serif', color: NAVY }
const cardSub = { font: '400 12px/1.4 Inter,sans-serif', color: SUB }

interface PainelScreenProps {
  mostrarOrigem: boolean
  limiarCritico: number
}

export function PainelScreen({ mostrarOrigem, limiarCritico }: PainelScreenProps) {
  const { pts, linePts, areaPath, grid, Y1 } = computeHistorico()
  const { fc, fcAvgY } = computeForecastBars()
  const teams = computeTeamPressure(limiarCritico)
  const critX = `${((limiarCritico / 40) * 100).toFixed(1)}%`

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 20 }}>
        <div style={cardStyle}>
          <span style={kicker}>Previsão D+1</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>124,5</span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>incidentes</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ padding: '4px 9px', borderRadius: 999, background: 'rgba(232,163,23,.12)', font: "500 11px/1.2 'JetBrains Mono',monospace", color: '#8a6210' }}>
              +9,7% vs média
            </span>
            <span style={{ font: '400 11px/1.2 Inter,sans-serif', color: SUB }}>média histórica 113,5/dia</span>
          </div>
          <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · PROPHET</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>Previsão D+7 · média/dia</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>115,8</span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>incidentes/dia</span>
          </div>
          <span style={{ font: '400 11px/1.4 Inter,sans-serif', color: SUB }}>
            Média aritmética dos 7 valores previstos D+1…D+7 (soma 810,5)
          </span>
          <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · PROPHET</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>Risco de OLA</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ font: '700 32px/1 Manrope,sans-serif', letterSpacing: '-.02em', color: '#8a6210' }}>Médio</span>
            <span style={{ font: "500 15px/1 'JetBrains Mono',monospace", color: MUTED }}>18,4%</span>
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'stretch' }}>
            <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(15,157,88,.25)' }} />
            <div style={{ flex: 1.5, height: 6, borderRadius: 3, background: '#E8A317' }} />
            <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(214,69,69,.25)' }} />
          </div>
          <span style={{ font: '400 11px/1.4 Inter,sans-serif', color: SUB }}>
            Faixas fixas sobre <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>pct_violacao_sla</span>: &lt;10% baixo · 10–25% médio · &gt;25% alto
          </span>
          <SourceTag visible={mostrarOrigem}>REGRA DETERMINÍSTICA</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>Volume base 2025</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>41.441</span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>incidentes</span>
          </div>
          <span style={{ font: '400 11px/1.4 Inter,sans-serif', color: SUB }}>Volume mensal estável entre 2.343 e 4.053 no ano</span>
          <SourceTag variant="historico" visible={mostrarOrigem}>HISTÓRICO · DW</SourceTag>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.55fr) minmax(0,1fr)', gap: 20 }}>
        <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px 20px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={cardTitle}>Histórico mensal — 2025</span>
              <span style={cardSub}>Contagem de incidentes por mês · escala mensal</span>
            </div>
            <SourceTag variant="historico" visible={mostrarOrigem}>HISTÓRICO · DW</SourceTag>
          </div>
          <svg viewBox="0 0 780 220" style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
            {grid.map((g, i) => (
              <line key={i} x1={44} x2={772} y1={g.y} y2={g.y} stroke="rgba(10,22,40,.07)" strokeWidth={1} />
            ))}
            <path d={areaPath} fill="rgba(30,111,217,.08)" />
            <polyline points={linePts} fill="none" stroke="#1E6FD9" strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
            {pts.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r={3.5} fill="#FFFFFF" stroke="#1E6FD9" strokeWidth={2} />
            ))}
            {grid.map((g, i) => (
              <text key={`gy${i}`} x={36} y={g.ty} textAnchor="end" fontFamily="JetBrains Mono, monospace" fontSize={10} fill={SUB}>
                {g.label}
              </text>
            ))}
            {pts.map((p, i) => (
              <text key={`mx${i}`} x={p.x} y={Y1 + 26} textAnchor="middle" fontFamily="Inter, sans-serif" fontSize={10} fill={SUB}>
                {p.label}
              </text>
            ))}
          </svg>
        </div>

        <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px 20px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={cardTitle}>Previsão D+1…D+7</span>
              <span style={cardSub}>Incidentes por dia · escala diária</span>
            </div>
            <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO</SourceTag>
          </div>
          <svg viewBox="0 0 380 220" style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
            <line x1={0} x2={380} y1={fcAvgY} y2={fcAvgY} stroke={SUB} strokeWidth={1} strokeDasharray="4 4" />
            <text x={380} y={fcAvgY - 6} textAnchor="end" fontFamily="JetBrains Mono, monospace" fontSize={10} fill={SUB}>
              média 115,8
            </text>
            {fc.map((b, i) => (
              <rect key={i} x={b.x} y={b.y} width={38} height={b.h} rx={6} fill={b.fill} />
            ))}
            {fc.map((b, i) => (
              <text key={`fv${i}`} x={b.cx} y={b.vy} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontSize={11} fontWeight={500} fill={NAVY}>
                {b.v}
              </text>
            ))}
            {fc.map((b, i) => (
              <text key={`fl${i}`} x={b.cx} y={208} textAnchor="middle" fontFamily="Inter, sans-serif" fontSize={10} fill={SUB}>
                {b.label}
              </text>
            ))}
          </svg>
        </div>
      </div>

      <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={cardTitle}>Pressão por equipe — D+1</span>
            <span style={cardSub}>Desvio do volume previsto frente à média histórica da própria equipe</span>
          </div>
          <SourceTag visible={mostrarOrigem}>REGRA · LIMIAR &gt;{limiarCritico}%</SourceTag>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {teams.map((t) => (
            <div key={t.name} style={{ display: 'grid', gridTemplateColumns: '88px 1fr 96px 104px', alignItems: 'center', gap: 16 }}>
              <span style={{ font: "500 13px/1 'JetBrains Mono',monospace", color: NAVY }}>{t.name}</span>
              <div style={{ position: 'relative', height: 12, borderRadius: 6, background: '#F0F3FF' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, borderRadius: 6, background: t.fill, width: t.w }} />
                <div style={{ position: 'absolute', top: -4, bottom: -4, width: 2, background: 'rgba(214,69,69,.55)', left: critX }} />
              </div>
              <span style={{ font: "500 13px/1 'JetBrains Mono',monospace", textAlign: 'right', color: t.fill }}>{t.pct}</span>
              <span
                style={{
                  justifySelf: 'start',
                  padding: '4px 9px',
                  borderRadius: 999,
                  font: '500 10px/1.3 Inter,sans-serif',
                  letterSpacing: '.02em',
                  background: t.badgeBg,
                  color: t.badgeFg,
                }}
              >
                {t.badge}
              </span>
            </div>
          ))}
        </div>
        <p style={{ margin: '18px 0 0', font: '400 12px/1.5 Inter,sans-serif', color: MUTED }}>
          Nenhuma equipe cruzou o limiar crítico (&gt;{limiarCritico}%) nesta execução. Todas as equipes de maior volume estão abaixo da própria média histórica em D+1.
        </p>
      </div>
    </section>
  )
}
