import { getPainel } from '../../lib/api'
import { useApi } from '../../lib/useApi'
import {
  computeForecastBars,
  computeHistorico,
  computeTeamPressure,
  nivelPressaoLabel,
  riscoOlaVisual,
  VOLUME_HISTORICO_2025,
} from '../../data/dashboardData'
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
  const { data, loading, error } = useApi(() => getPainel({ dias: 30 }), [])

  if (loading) return <Loading />
  if (error || !data) return <ErrorState error={error ?? 'sem dado'} />

  const historico = data.serie.filter((p) => p.tipo === 'historico')
  const previsao = data.serie.filter((p) => p.tipo === 'previsao')
  const { pts, linePts, areaPath, grid, Y1 } = computeHistorico(historico)
  const { fc, fcAvgY } = computeForecastBars(previsao, data.previsao_d7_media.valor)
  const { rows: teams, maxAbs: pressaoMaxAbs } = computeTeamPressure(data.pressao_equipes, limiarCritico)
  const critX = `${Math.min(100, (limiarCritico / pressaoMaxAbs) * 100).toFixed(1)}%`
  const risco = riscoOlaVisual(data.risco_ola.nivel)
  const equipeCritica = data.pressao_equipes.find((e) => e.nivel_pressao === 'critico')
  const equipeAtencao = data.pressao_equipes.filter((e) => e.nivel_pressao !== 'normal')

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 20 }}>
        <div style={cardStyle}>
          <span style={kicker}>Previsão D+1 · {data.previsao_d1.data}</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>
              {data.previsao_d1.valor.toLocaleString('pt-BR')}
            </span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>incidentes</span>
          </div>
          {data.previsao_d1.metodologia && (
            <span style={{ font: '400 11px/1.3 Inter,sans-serif', color: SUB }}>proporção histórica (não é modelo por corte)</span>
          )}
          <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · PROPHET</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>Previsão D+7 · média/dia</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>
              {data.previsao_d7_media.valor.toLocaleString('pt-BR')}
            </span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>incidentes/dia</span>
          </div>
          <span style={{ font: '400 11px/1.4 Inter,sans-serif', color: SUB }}>
            {data.previsao_d7_media.variacao_pct_vs_media_historica >= 0 ? '+' : ''}
            {data.previsao_d7_media.variacao_pct_vs_media_historica.toFixed(1).replace('.', ',')}% vs. média histórica diária
          </span>
          <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · PROPHET</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>Risco de OLA</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ font: '700 32px/1 Manrope,sans-serif', letterSpacing: '-.02em', color: risco.color }}>{risco.label}</span>
            <span style={{ font: "500 15px/1 'JetBrains Mono',monospace", color: MUTED }}>
              {data.risco_ola.pct_violacao_media_movel.toFixed(2).replace('.', ',')}%
            </span>
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'stretch' }}>
            <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(15,157,88,.25)' }} />
            <div style={{ flex: 1.5, height: 6, borderRadius: 3, background: '#E8A317' }} />
            <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'rgba(214,69,69,.25)' }} />
          </div>
          <span style={{ font: '400 11px/1.4 Inter,sans-serif', color: SUB }}>
            Média móvel de <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>pct_violacao_sla</span> nos últimos{' '}
            {data.risco_ola.janela_dias} dias
          </span>
          <SourceTag visible={mostrarOrigem}>REGRA DETERMINÍSTICA</SourceTag>
        </div>

        <div style={cardStyle}>
          <span style={kicker}>Volume base 2025</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ font: "600 40px/1 'JetBrains Mono',monospace", letterSpacing: '-.02em', color: NAVY }}>
              {VOLUME_HISTORICO_2025.toLocaleString('pt-BR')}
            </span>
            <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>incidentes</span>
          </div>
          <span style={{ font: '400 11px/1.4 Inter,sans-serif', color: SUB }}>
            Total do ano encerrado — volume mensal estável entre 2.343 e 4.053
          </span>
          <SourceTag variant="historico" visible={mostrarOrigem}>HISTÓRICO · DW</SourceTag>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.55fr) minmax(0,1fr)', gap: 20 }}>
        <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px 20px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={cardTitle}>Histórico — últimos {historico.length} dias</span>
              <span style={cardSub}>Contagem diária de incidentes</span>
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
              média {data.previsao_d7_media.valor.toLocaleString('pt-BR')}
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
          {equipeCritica
            ? `${equipeCritica.grupo_designado} cruzou o limiar crítico (>${limiarCritico}%) nesta execução.`
            : equipeAtencao.length > 0
              ? `Nenhuma equipe cruzou o limiar crítico (>${limiarCritico}%) nesta execução. ${equipeAtencao.length} equipe(s) em nível ${nivelPressaoLabel('atencao')}.`
              : `Nenhuma equipe cruzou o limiar crítico (>${limiarCritico}%) nesta execução — todas as equipes estão em nível normal.`}
        </p>
      </div>
    </section>
  )
}
