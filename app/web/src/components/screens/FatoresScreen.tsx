import { Fragment } from 'react'
import { computeHeatmap, computeImportanciaFeatures, computeShapExplicacao } from '../../data/dashboardData'
import { MUTED, NAVY, SUB } from '../../lib/theme'
import { SourceTag } from '../SourceTag'

const cardTitle = { font: '600 20px/1.2 Manrope,sans-serif', color: NAVY }
const cardSub = { font: '400 12px/1.4 Inter,sans-serif', color: SUB }

interface FatoresScreenProps {
  mostrarOrigem: boolean
}

export function FatoresScreen({ mostrarOrigem }: FatoresScreenProps) {
  const feats = computeImportanciaFeatures()
  const shap = computeShapExplicacao()
  const { dows, heat } = computeHeatmap()

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.15fr) minmax(0,1fr)', gap: 20 }}>
        <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={cardTitle}>Importância dos fatores</span>
              <span style={cardSub}>
                Valores de <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>ml.fct_importancia_conceito</span>
              </span>
            </div>
            <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · XGBOOST</SourceTag>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
            {feats.map((f) => (
              <div key={f.name} style={{ display: 'grid', gridTemplateColumns: '196px 1fr 62px', alignItems: 'center', gap: 14 }}>
                <span style={{ font: '500 13px/1.3 Inter,sans-serif', color: NAVY }}>{f.name}</span>
                <div style={{ height: 14, borderRadius: 7, background: '#F0F3FF', overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 7, background: f.fill, width: f.w }} />
                </div>
                <span style={{ font: "500 13px/1 'JetBrains Mono',monospace", textAlign: 'right', color: NAVY }}>{f.v}</span>
              </div>
            ))}
          </div>
          <p style={{ margin: '18px 0 0', font: '400 12px/1.55 Inter,sans-serif', color: MUTED }}>
            Dia da semana é o fator de menor peso do modelo (1,23%). As features de maior peso são estruturais: prioridade, carga do time e triagem por categoria.
          </p>
        </div>

        <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={cardTitle}>Por que este incidente tem risco elevado</span>
              <span style={cardSub}>
                SHAP para <span style={{ fontFamily: "'JetBrains Mono',monospace" }}>INC0048213</span> — um dos 30 incidentes de maior risco individual
              </span>
            </div>
            <SourceTag variant="modelo" visible={mostrarOrigem}>MODELO · XGBOOST</SourceTag>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, margin: '14px 0 18px' }}>
            <span style={{ font: "600 30px/1 'JetBrains Mono',monospace", color: '#D64545' }}>0,86</span>
            <span style={{ font: '400 12px/1.4 Inter,sans-serif', color: SUB }}>risco de violação de OLA · base do modelo 0,18</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {shap.map((s) => (
              <div key={s.name} style={{ display: 'grid', gridTemplateColumns: '170px 1fr 56px', alignItems: 'center', gap: 12 }}>
                <span style={{ font: '500 12px/1.3 Inter,sans-serif', color: NAVY }}>{s.name}</span>
                <div style={{ position: 'relative', height: 14, borderRadius: 4, background: '#F9F9FF' }}>
                  <div style={{ position: 'absolute', top: 0, bottom: 0, width: 1, background: 'rgba(10,22,40,.18)', left: '50%' }} />
                  <div style={{ position: 'absolute', top: 2, bottom: 2, borderRadius: 3, background: s.fill, left: s.left, width: s.w }} />
                </div>
                <span style={{ font: "500 12px/1 'JetBrains Mono',monospace", textAlign: 'right', color: s.fill }}>{s.v}</span>
              </div>
            ))}
          </div>
          <p style={{ margin: '18px 0 0', font: '400 12px/1.55 Inter,sans-serif', color: MUTED }}>
            Esta explicação é do classificador de risco por incidente. A previsão de volume do dia seguinte vem do Prophet, que não produz valores SHAP.
          </p>
        </div>
      </div>

      <div style={{ background: '#FFFFFF', borderRadius: 16, padding: '24px 28px', boxShadow: '0 4px 16px rgba(10,22,40,.03)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={cardTitle}>Categoria × dia da semana</span>
            <span style={cardSub}>Volume médio de abertura · agregação calculada, sem tabela dedicada</span>
          </div>
          <SourceTag variant="calculado" visible={mostrarOrigem}>CALCULADO · DW</SourceTag>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: `84px repeat(${dows.length},minmax(0,1fr))`, gap: 6, alignItems: 'center' }}>
          <span />
          {dows.map((d) => (
            <span key={d} style={{ font: '600 11px/1 Inter,sans-serif', textAlign: 'center', letterSpacing: '.04em', color: SUB }}>
              {d}
            </span>
          ))}
          {heat.map((row) => (
            <Fragment key={row.cat}>
              <span style={{ font: "500 12px/1 'JetBrains Mono',monospace", color: NAVY }}>
                {row.cat}
              </span>
              {row.cells.map((c, i) => (
                <div
                  key={i}
                  style={{
                    height: 42,
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: "'JetBrains Mono',monospace",
                    fontSize: 12,
                    fontWeight: 500,
                    background: c.bg,
                    color: c.fg,
                  }}
                >
                  {c.v}
                </div>
              ))}
            </Fragment>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 18 }}>
          <span style={{ font: '600 10px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.08em', color: SUB }}>Menor</span>
          <div style={{ flex: '0 0 220px', height: 8, borderRadius: 4, background: 'linear-gradient(90deg,#F0F3FF,#1E6FD9)' }} />
          <span style={{ font: '600 10px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.08em', color: SUB }}>Maior</span>
        </div>
      </div>
    </section>
  )
}
