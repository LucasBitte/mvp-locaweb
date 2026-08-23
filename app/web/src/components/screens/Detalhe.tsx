import { useEffect, useState } from 'react'
import { DetalheResponse } from '../../types'
import { fetchAPI } from '../../lib/api'

export default function Detalhe() {
  const [data, setData] = useState<DetalheResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAPI('/detalhe').then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-4">Carregando...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Forecast & Capacidade</h1>
      <div className="p-6 bg-white rounded-lg border border-slate-200">
        <h2 className="font-semibold mb-4">Previsão por Categoria</h2>
        <table className="w-full text-sm">
          <thead><tr className="border-b"><th className="text-left py-2">Categoria</th><th className="text-right">Volume</th><th className="text-right">Δ%</th></tr></thead>
          <tbody>
            {data?.previsao_por_categoria.map(c => (
              <tr key={c.categoria} className="border-b"><td>{c.categoria}</td><td className="text-right">{c.yhat.toFixed(0)}</td><td className="text-right">{c.delta_pct.toFixed(1)}%</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
