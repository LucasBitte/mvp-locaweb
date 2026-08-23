export default function Sobre() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Sobre o Projeto</h1>
      <div className="grid gap-4">
        <div className="p-6 bg-white rounded-lg border border-slate-200">
          <h2 className="text-lg font-semibold mb-2">Framework AIOps</h2>
          <p className="text-sm text-slate-600">PREVER → PRIORIZAR → EXPLICAR → SEGMENTAR → AGIR</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Card title="Previsão" desc="Prophet (D+1..D+7)" />
          <Card title="Priorização" desc="Risco & Clustering" />
          <Card title="Explicabilidade" desc="SHAP + Importância" />
          <Card title="Ações" desc="Regras & Alertas" />
        </div>
      </div>
    </div>
  )
}

function Card({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
      <div className="font-semibold text-blue-900">{title}</div>
      <div className="text-sm text-blue-700">{desc}</div>
    </div>
  )
}
