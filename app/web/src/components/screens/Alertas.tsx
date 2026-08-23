import { useEffect, useState } from 'react'
import { AlertasResponse, Alerta } from '../../types'
import { fetchAPI } from '../../lib/api'
import SourceNote from '../SourceNote'

const SEVERIDADE_COR: Record<string, string> = {
  crítica: 'bg-red-100 text-red-800 border-red-200',
  alta: 'bg-orange-100 text-orange-800 border-orange-200',
  média: 'bg-amber-100 text-amber-800 border-amber-200',
  baixa: 'bg-slate-100 text-slate-600 border-slate-200',
}

const STATUS_COR: Record<string, string> = {
  ok: 'bg-green-100 text-green-800',
  degradado: 'bg-amber-100 text-amber-800',
  abaixo_meta: 'bg-red-100 text-red-800',
}

export default function Alertas() {
  const [data, setData] = useState<AlertasResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAPI('/alertas').then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-4">Carregando...</div>
  if (!data) return <div className="p-4 text-red-600">Erro ao carregar dados</div>

  const semAlertas = data.alertas_ativos.length === 0
  const semRecomendacoes = data.recomendacoes.length === 0

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">05 · Ações &amp; Governança</h1>
      <p className="text-sm text-slate-500 -mt-4">O que fazer, com qual evidência, com qual confiança.</p>

      <section>
        <h2 className="text-lg font-semibold text-slate-700 mb-3">Alertas ativos</h2>
        {semAlertas ? (
          <p className="text-sm text-slate-500">Nenhum alerta ativo no momento.</p>
        ) : (
          <div className="space-y-2">
            {data.alertas_ativos.map((a) => (
              <AlertaCard key={a.id} alerta={a} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-700 mb-3">Recomendações</h2>
        {semRecomendacoes ? (
          <SourceNote kind="sem-fonte" label="/api/alertas.recomendacoes ainda não implementado" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.recomendacoes.map((r) => (
              <div key={r.id} className="p-4 bg-white rounded-lg border border-slate-200">
                <div className="font-medium text-sm">{r.acao}</div>
                <div className="text-xs text-slate-500 mt-1">Responsável: {r.owner} · {r.prioridade}</div>
                <div className="text-xs text-slate-400">{r.origem === 'modelo' ? 'MODELO' : 'REGRA'}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-lg font-semibold text-slate-700">Saúde dos modelos</h2>
          <SourceNote kind="fixo" label="valores de auditoria" />
        </div>
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2">Modelo</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Métrica-chave</th>
                <th className="px-4 py-2">Limitação</th>
              </tr>
            </thead>
            <tbody>
              {data.saude_modelos.map((m) => (
                <tr key={m.modelo} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-medium">{m.modelo}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COR[m.status] ?? 'bg-slate-100 text-slate-600'}`}>
                      {m.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">{m.metrica_chave}</td>
                  <td className="px-4 py-2 text-slate-600">{m.limitacao}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-700 mb-3">Rastreabilidade por alerta</h2>
        {semAlertas ? (
          <p className="text-sm text-slate-500">Sem alertas para rastrear.</p>
        ) : (
          <div className="space-y-1">
            {data.alertas_ativos.map((a) => (
              <div key={a.id} className="flex items-center gap-2 text-xs text-slate-500 px-2">
                <span className="font-mono">{a.id}</span>
                <span>→</span>
                <span>{a.origem === 'modelo' ? 'MODELO' : 'REGRA'}</span>
                <span>→</span>
                <span>{a.cluster_id ? `cluster ${a.cluster_id}` : a.equipe_id ? `equipe ${a.equipe_id}` : '—'}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-700 mb-3">Limitações do sistema</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.limitacoes_sistema.map((l, i) => (
            <div key={i} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-sm text-slate-600">
              {l}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function AlertaCard({ alerta }: { alerta: Alerta }) {
  return (
    <div className={`p-3 rounded-lg border flex items-center justify-between ${SEVERIDADE_COR[alerta.severidade] ?? SEVERIDADE_COR.baixa}`}>
      <div>
        <span className="text-xs font-semibold uppercase mr-2">{alerta.severidade}</span>
        <span className="text-sm">{alerta.condicao}</span>
      </div>
      <span className="text-xs opacity-70">{alerta.origem === 'modelo' ? 'MODELO' : 'REGRA'}</span>
    </div>
  )
}
