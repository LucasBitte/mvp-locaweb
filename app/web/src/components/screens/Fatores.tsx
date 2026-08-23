import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, LineChart, Line, ScatterChart, Scatter,
} from 'recharts'
import { FatoresResponse } from '../../types'
import { fetchAPI } from '../../lib/api'
import SourceNote from '../SourceNote'

export default function Fatores() {
  const [data, setData] = useState<FatoresResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    fetchAPI('/fatores').then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selectedId == null) return
    fetchAPI('/fatores', { incidente_id: selectedId }).then(setData).catch(console.error)
  }, [selectedId])

  if (loading) return <div className="p-4">Carregando...</div>
  if (!data) return <div className="p-4 text-red-600">Erro ao carregar dados</div>

  const scoreBins = buildBins(data.ranking_incidentes.map((r) => r.score_calibrado), 8)
  const importanciaData = Object.entries(data.importancia_global)
    .sort((a, b) => b[1] - a[1])
    .map(([conceito, importance_pct]) => ({ conceito, importance_pct }))
  const cm = data.qualidade_modelo.confusion_matrix
  const prevalencia = (cm.tp + cm.fn) / Math.max(1, cm.tp + cm.fp + cm.fn + cm.tn)
  const heatmapDisponivel = Object.keys(data.heatmap_categoria_dia).length > 0

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">03 · Risco &amp; Explicabilidade</h1>
      <p className="text-sm text-slate-500 -mt-4">Quais incidentes merecem atenção e por quê.</p>

      {/* 03.1 — Decisão */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-slate-700">Priorização</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-3">Ranking — Top 30 por risco</h3>
            <div className="overflow-y-auto max-h-80">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-1">Incidente</th>
                    <th>Prioridade</th>
                    <th>Categoria</th>
                    <th className="text-right">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ranking_incidentes.map((r) => (
                    <tr
                      key={r.incidente_id}
                      onClick={() => setSelectedId(r.incidente_id)}
                      className={`border-b cursor-pointer hover:bg-blue-50 ${selectedId === r.incidente_id ? 'bg-blue-50' : ''}`}
                    >
                      <td className="py-1">{r.incidente_id}</td>
                      <td>{r.prioridade}</td>
                      <td>{r.categoria}</td>
                      <td className="text-right font-medium">{(r.score_calibrado * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-slate-400 mt-2">Clique numa linha para ver a explicação SHAP abaixo.</p>
          </div>

          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-1">Distribuição dos scores (Top 30)</h3>
            <p className="text-xs text-slate-400 mb-3">Não representa a população total de incidentes, só o ranking retornado.</p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={scoreBins}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <ReferenceLine x={binLabelForThreshold(scoreBins, data.qualidade_modelo.threshold_atual)} stroke="#dc2626" strokeDasharray="4 4" />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* 03.2 — Explicação */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-slate-700">Explicação</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-3">SHAP do incidente selecionado</h3>
            {!selectedId && <p className="text-sm text-slate-500">Selecione um incidente no ranking acima.</p>}
            {selectedId && !data.shap_decomposicao && (
              <div className="space-y-2">
                <SourceNote kind="sem-fonte" label="ml_dev.fct_shap_incidente ainda vazia" />
                <p className="text-xs text-slate-400">A decomposição SHAP depende da Fase 5 (migração ml_dev → ml).</p>
              </div>
            )}
            {data.shap_decomposicao && (
              <ShapWaterfall shap={data.shap_decomposicao} />
            )}
          </div>

          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-3">Importância global (por conceito)</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={importanciaData} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="conceito" width={110} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: any) => `${Number(v).toFixed(1)}%`} />
                <Bar dataKey="importance_pct" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* 03.3 — Qualidade do modelo */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-slate-700">Qualidade do modelo (XGBoost)</h2>
          <SourceNote kind="fixo" label="valores de auditoria" />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <MetricCard label="AUC-ROC" value={data.qualidade_modelo.auc_roc.toFixed(4)} sub="meta 0,85" />
          <MetricCard label="MCC" value={data.qualidade_modelo.mcc.toFixed(3)} sub="mais honesto que F1" />
          <MetricCard label="Brier" value={data.qualidade_modelo.brier.toFixed(4)} />
          <MetricCard label="Prevalência" value={`${(prevalencia * 100).toFixed(1)}%`} />
          <MetricCard label="Threshold" value={data.qualidade_modelo.threshold_atual.toFixed(2)} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-3">Matriz de confusão</h3>
            <ConfusionMatrix cm={cm} />
          </div>

          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-3">AUC por prioridade</h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={Object.entries(data.qualidade_modelo.auc_por_prioridade).map(([prioridade, auc]) => ({ prioridade, auc }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="prioridade" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <ReferenceLine y={data.qualidade_modelo.auc_roc} stroke="#94a3b8" strokeDasharray="4 4" />
                <Bar dataKey="auc" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="text-xs text-slate-400 mt-1">Linha tracejada = AUC agregado ({data.qualidade_modelo.auc_roc.toFixed(2)}).</p>
          </div>

          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-3">Calibration curve</h3>
            <ResponsiveContainer width="100%" height={180}>
              <ScatterChart margin={{ left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" dataKey="x" domain={[0, 1]} name="predito" tick={{ fontSize: 11 }} />
                <YAxis type="number" dataKey="y" domain={[0, 1]} name="real" tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: any) => Number(v).toFixed(2)} />
                <Scatter data={data.qualidade_modelo.calibration_curve.map(([x, y]) => ({ x, y }))} fill="#16a34a" />
                <Line type="linear" dataKey="y" data={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#cbd5e1" strokeDasharray="4 4" dot={false} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="p-4 bg-white rounded-lg border border-slate-200">
          <h3 className="font-medium mb-2">Heatmap categoria × dia</h3>
          {heatmapDisponivel ? (
            <p className="text-sm text-slate-500">Renderização pendente.</p>
          ) : (
            <SourceNote kind="sem-fonte" label="/api/fatores.heatmap_categoria_dia ainda não implementado" />
          )}
        </div>
      </section>
    </div>
  )
}

function ShapWaterfall({ shap }: { shap: NonNullable<FatoresResponse['shap_decomposicao']> }) {
  const steps = Object.entries(shap.shap_values).map(([feature, value]) => ({ feature, value }))
  const rows = [
    { label: 'base_value', value: shap.base_value },
    ...steps,
    { label: 'saída bruta XGBoost', value: shap.saida_bruta_xgboost, isTotal: true },
    { label: 'score calibrado (isotônico)', value: shap.score_calibrado, isTotal: true },
  ]
  return (
    <div className="space-y-1">
      {rows.map((r, i) => (
        <div key={i} className={`flex justify-between text-sm px-2 py-1 rounded ${'isTotal' in r && r.isTotal ? 'bg-slate-100 font-semibold' : ''}`}>
          <span>{'feature' in r ? r.feature : r.label}</span>
          <span>{r.value.toFixed(4)}</span>
        </div>
      ))}
      <p className="text-xs text-slate-400 pt-1">Calibração isotônica é etapa separada — SHAP explica a saída bruta, não o score final.</p>
    </div>
  )
}

function ConfusionMatrix({ cm }: { cm: { tp: number; fp: number; fn: number; tn: number } }) {
  const max = Math.max(cm.tp, cm.fp, cm.fn, cm.tn, 1)
  const cell = (label: string, value: number) => (
    <div
      className="rounded p-3 text-center"
      style={{ backgroundColor: `rgba(59,130,246,${0.15 + 0.65 * (value / max)})` }}
    >
      <div className="text-xs text-slate-600">{label}</div>
      <div className="text-lg font-bold">{value}</div>
    </div>
  )
  return (
    <div className="grid grid-cols-2 gap-2">
      {cell('TP', cm.tp)}
      {cell('FP', cm.fp)}
      {cell('FN', cm.fn)}
      {cell('TN', cm.tn)}
    </div>
  )
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="p-3 bg-white rounded-lg border border-slate-200">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-xl font-bold text-slate-800">{value}</div>
      {sub && <div className="text-xs text-slate-400">{sub}</div>}
    </div>
  )
}

function buildBins(values: number[], n: number) {
  if (values.length === 0) return []
  const min = Math.min(...values)
  const max = Math.max(...values)
  const width = (max - min) / n || 1
  const bins = Array.from({ length: n }, (_, i) => ({
    label: `${(min + i * width).toFixed(2)}`,
    count: 0,
    lo: min + i * width,
    hi: min + (i + 1) * width,
  }))
  for (const v of values) {
    const idx = Math.min(n - 1, Math.floor((v - min) / width))
    bins[idx].count++
  }
  return bins
}

function binLabelForThreshold(bins: ReturnType<typeof buildBins>, threshold: number) {
  const match = bins.find((b) => threshold >= b.lo && threshold < b.hi)
  return match?.label ?? bins[bins.length - 1]?.label
}
