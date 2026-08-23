import { useEffect, useState } from 'react'
import { PainelResponse } from '../../types'
import { fetchAPI } from '../../lib/api'

export default function Painel() {
  const [data, setData] = useState<PainelResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAPI('/painel').then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-4">Carregando...</div>
  if (!data) return <div className="p-4 text-red-600">Erro ao carregar dados</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Visão Estratégica</h1>
      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Total de Chamados" value={data.total_chamados} />
        <MetricCard label="OLA Status (%)" value={data.kpi_status_agregado.toFixed(1)} />
        <MetricCard label="Previsão D+1" value={data.previsao_d1.yhat.toFixed(0)} />
        <MetricCard label="Pressão Média" value={data.pressao_d1_a_d7_media.toFixed(1)} />
      </div>
      <div className="p-6 bg-white rounded-lg border border-slate-200">
        <h2 className="font-semibold mb-2">Detalhes</h2>
        <p className="text-sm text-slate-600">Categoria Top: {data.forecast_top_categoria}</p>
        <p className="text-sm text-slate-600">Risco Principal: {data.risco_principal}</p>
      </div>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200">
      <div className="text-xs font-semibold text-blue-700">{label}</div>
      <div className="text-2xl font-bold text-blue-900 mt-1">{value}</div>
    </div>
  )
}
