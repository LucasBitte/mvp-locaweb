function App() {
  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-10 text-center max-w-md">
        <h1 className="text-lg font-semibold text-slate-800">
          MVP Locaweb — AIOps Incidentes
        </h1>
        <p className="text-sm text-slate-500 mt-2">
          Setup inicial concluído. Painéis (Painel, Detalhe, KPI, Fatores,
          Clusters, Alertas) chegam na etapa de dashboard-web, consumindo a
          API sobre o modelo dimensional.
        </p>
      </div>
    </div>
  )
}

export default App
