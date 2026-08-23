import { useEffect, useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, LineChart, Line, Cell,
} from 'recharts'
import { ClustersResponse, PerfilCluster } from '../../types'
import { fetchAPI } from '../../lib/api'
import SourceNote from '../SourceNote'

export default function Clusters() {
  const [data, setData] = useState<ClustersResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    fetchAPI('/clusters').then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-4">Carregando...</div>
  if (!data) return <div className="p-4 text-red-600">Erro ao carregar dados</div>

  const impactoOrdenado = [...data.clusters].sort((a, b) => b.impacto_volume_excedencia_pct - a.impacto_volume_excedencia_pct)
  const composicaoDisponivel = Object.keys(data.composicao_por_prioridade).length > 0
  const heatmapDisponivel = Object.keys(data.composicao_por_categoria).length > 0

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">04 · Perfis Operacionais</h1>
      <p className="text-sm text-slate-500 -mt-4">Que tipos de comportamento existem e onde concentram os problemas.</p>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-4 bg-white rounded-lg border border-slate-200">
          <h3 className="font-medium mb-3">Duração × Excedência × Volume</h3>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" dataKey="duracao_media_horas" name="duração (h)" tick={{ fontSize: 11 }} />
              <YAxis type="number" dataKey="taxa_excedeu_tempo_esperado_pct" name="excedência (%)" tick={{ fontSize: 11 }} />
              <ZAxis type="number" dataKey="pct_volume" range={[100, 1000]} name="volume (%)" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<ClusterTooltip />} />
              <Scatter data={data.clusters}>
                {data.clusters.map((c) => (
                  <Cell key={c.cluster_id} fill={c.cor_hex} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <p className="text-xs text-slate-400">Tamanho da bolha = participação no volume total.</p>
        </div>

        <div className="p-4 bg-white rounded-lg border border-slate-200">
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-medium">Impacto por volume e excedência</h3>
          </div>
          <p className="text-xs text-slate-400 mb-3">
            Regra inicial de 2 fatores (pct_volume × taxa de excedência) — ponto de partida para discussão, não veredito causal nem definitivo.
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={impactoOrdenado} layout="vertical" margin={{ left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="nome_perfil" width={140} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: any) => `${Number(v).toFixed(1)}%`} />
              <Bar dataKey="impacto_volume_excedencia_pct" radius={[0, 4, 4, 0]}>
                {impactoOrdenado.map((c) => (
                  <Cell key={c.cluster_id} fill={c.cor_hex} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-700 mb-3">Perfis</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {data.clusters.map((c) => (
            <ClusterCard key={c.cluster_id} cluster={c} selected={selected === c.cluster_id} onClick={() => setSelected(c.cluster_id)} />
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-4 bg-white rounded-lg border border-slate-200">
          <h3 className="font-medium mb-2">Composição por prioridade</h3>
          {composicaoDisponivel ? (
            <p className="text-sm text-slate-500">Renderização pendente.</p>
          ) : (
            <SourceNote kind="sem-fonte" label="/api/clusters.composicao_por_prioridade ainda vazio" />
          )}
        </div>
        <div className="p-4 bg-white rounded-lg border border-slate-200">
          <h3 className="font-medium mb-2">Composição por categoria</h3>
          {heatmapDisponivel ? (
            <p className="text-sm text-slate-500">Renderização pendente.</p>
          ) : (
            <SourceNote kind="sem-fonte" label="/api/clusters.composicao_por_categoria ainda vazio" />
          )}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-slate-700">Qualidade da clusterização</h2>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-2 text-sm">Silhouette × k</h3>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={data.diagnostico_kmeans}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="k" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="silhouette" stroke="#3b82f6" dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <h3 className="font-medium mb-2 text-sm">Davies-Bouldin × k</h3>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={data.diagnostico_kmeans}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="k" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="davies_bouldin" stroke="#f97316" dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="p-4 bg-white rounded-lg border border-slate-200">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-medium text-sm">% Variância PCA (PC1+PC2)</h3>
              <SourceNote kind="fixo" label="mesmo valor p/ todo k" />
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={data.diagnostico_kmeans}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="k" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
                <Tooltip formatter={(v: any) => `${Number(v).toFixed(1)}%`} />
                <Line type="monotone" dataKey="pca_variancia" stroke="#8b5cf6" dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <p className="text-xs text-slate-400">k=4 não é o ótimo estatístico em nenhuma métrica — é decisão de negócio documentada.</p>

        <div className="p-4 bg-white rounded-lg border border-slate-200">
          <h3 className="font-medium mb-2">PCA scatter (PC1 × PC2)</h3>
          <SourceNote kind="sem-fonte" label="sem endpoint de coordenadas PCA por incidente" />
        </div>
      </section>
    </div>
  )
}

function ClusterTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const c: PerfilCluster = payload[0].payload
  return (
    <div className="bg-white border border-slate-200 rounded p-2 text-xs shadow-sm">
      <div className="font-semibold">{c.nome_perfil}</div>
      <div>Duração média: {c.duracao_media_horas.toFixed(0)}h</div>
      <div>Excedência: {c.taxa_excedeu_tempo_esperado_pct.toFixed(1)}%</div>
      <div>Volume: {c.pct_volume.toFixed(1)}%</div>
    </div>
  )
}

function ClusterCard({ cluster, selected, onClick }: { cluster: PerfilCluster; selected: boolean; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border cursor-pointer transition ${selected ? 'border-blue-400 ring-2 ring-blue-100' : 'border-slate-200'}`}
      style={{ borderLeftColor: cluster.cor_hex, borderLeftWidth: 4 }}
    >
      <div className="font-semibold text-sm">{cluster.nome_perfil}</div>
      <div className="text-xs text-slate-500 mt-1">{cluster.n_incidentes.toLocaleString('pt-BR')} incidentes · {cluster.pct_volume.toFixed(1)}% do volume</div>
      <div className="text-xs text-slate-500">Duração média: {cluster.duracao_media_horas.toFixed(0)}h</div>
      <div className="text-xs text-slate-500">Excedência: {cluster.taxa_excedeu_tempo_esperado_pct.toFixed(1)}%</div>
    </div>
  )
}
