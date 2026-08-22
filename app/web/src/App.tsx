import { useState } from 'react'
import { AlertasScreen } from './components/screens/AlertasScreen'
import { ClustersScreen } from './components/screens/ClustersScreen'
import { DetalheScreen } from './components/screens/DetalheScreen'
import { FatoresScreen } from './components/screens/FatoresScreen'
import { KpiScreen } from './components/screens/KpiScreen'
import { PainelScreen } from './components/screens/PainelScreen'
import { Header } from './components/Header'
import { BG } from './lib/theme'

// Limiar de pressão crítica por equipe (PLAN.md Fase 3, ml.fct_pressao_equipe.nivel_pressao).
const LIMIAR_CRITICO_PCT = 30
// Mostra os selos de origem do dado (MODELO/REGRA/HISTÓRICO) em todo card —
// governança do desafio: nunca deixar implícito se um número vem de ML ou de regra.
const MOSTRAR_ORIGEM = true

function App() {
  const [tab, setTab] = useState(0)

  return (
    <div style={{ minHeight: '100vh', background: BG, padding: '0 0 64px' }}>
      <Header activeTab={tab} onSelectTab={setTab} />
      <main style={{ maxWidth: 1360, margin: '0 auto', padding: '32px 40px 0' }}>
        {tab === 0 && <PainelScreen mostrarOrigem={MOSTRAR_ORIGEM} limiarCritico={LIMIAR_CRITICO_PCT} />}
        {tab === 1 && <DetalheScreen mostrarOrigem={MOSTRAR_ORIGEM} />}
        {tab === 2 && <KpiScreen mostrarOrigem={MOSTRAR_ORIGEM} />}
        {tab === 3 && <FatoresScreen mostrarOrigem={MOSTRAR_ORIGEM} />}
        {tab === 4 && <ClustersScreen mostrarOrigem={MOSTRAR_ORIGEM} />}
        {tab === 5 && <AlertasScreen mostrarOrigem={MOSTRAR_ORIGEM} limiarCritico={LIMIAR_CRITICO_PCT} />}
      </main>
    </div>
  )
}

export default App
