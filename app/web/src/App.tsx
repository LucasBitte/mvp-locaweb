import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Sobre from './components/screens/Sobre'
import Painel from './components/screens/Painel'
import Detalhe from './components/screens/Detalhe'
import Fatores from './components/screens/Fatores'
import Clusters from './components/screens/Clusters'
import Alertas from './components/screens/Alertas'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        {/* Header + Navegação */}
        <nav className="bg-white border-b border-slate-200 sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-800 mr-6">AIOps Dashboard</h1>
            <div className="flex gap-1">
              <Link to="/sobre" className="nav-link">Sobre</Link>
              <Link to="/painel" className="nav-link">01 Visão Estratégica</Link>
              <Link to="/detalhe" className="nav-link">02 Forecast</Link>
              <Link to="/fatores" className="nav-link">03 Risco</Link>
              <Link to="/clusters" className="nav-link">04 Perfis</Link>
              <Link to="/alertas" className="nav-link">05 Ações</Link>
            </div>
          </div>
        </nav>

        {/* Conteúdo */}
        <div className="max-w-7xl mx-auto p-4">
          <Routes>
            <Route path="/sobre" element={<Sobre />} />
            <Route path="/painel" element={<Painel />} />
            <Route path="/detalhe" element={<Detalhe />} />
            <Route path="/fatores" element={<Fatores />} />
            <Route path="/clusters" element={<Clusters />} />
            <Route path="/alertas" element={<Alertas />} />
            <Route path="/" element={<Sobre />} />
          </Routes>
        </div>
      </div>

      <style>{`
        .nav-link {
          padding: 0.5rem 0.75rem;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          color: #64748b;
          transition: all 0.2s;
        }
        .nav-link:hover {
          background: #f1f5f9;
          color: #334155;
        }
      `}</style>
    </BrowserRouter>
  )
}

export default App
