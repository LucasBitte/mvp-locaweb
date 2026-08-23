import { MUTED, NAVY, SUB } from '../lib/theme'

export const TABS: { name: string; sub: string }[] = [
  { name: 'Painel', sub: 'Visão geral' },
  { name: 'Detalhe', sub: 'Operação' },
  { name: 'KPI', sub: 'OLA & Metas' },
  { name: 'Fatores', sub: 'Fatores de Risco' },
  { name: 'Clusters', sub: 'Perfis Operacionais' },
  { name: 'Alertas', sub: 'Alertas & Ações' },
]

interface HeaderProps {
  activeTab: number
  onSelectTab: (i: number) => void
}

export function Header({ activeTab, onSelectTab }: HeaderProps) {
  return (
    <header
      className="px-4 sm:px-6 lg:px-10"
      style={{
        background: '#F0F3FF',
        position: 'sticky',
        top: 0,
        zIndex: 20,
        backdropFilter: 'saturate(140%) blur(20px)',
      }}
    >
      <div className="max-w-[1360px] mx-auto flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between sm:gap-8">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingBottom: 14 }}>
          <span style={{ font: '600 12px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.05em', color: SUB }}>
            Locaweb · FIAP · AIOps
          </span>
          <span style={{ font: "700 22px/1.1 Manrope,sans-serif", letterSpacing: '-.02em', color: '#101C2E' }}>
            Incidentes de TI — Observabilidade preditiva
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingBottom: 14 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 3 }}>
            <span style={{ font: '600 10px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.08em', color: SUB }}>
              Origem dos dados
            </span>
            <span style={{ font: "500 13px/1 'JetBrains Mono',monospace", color: MUTED }}>dw · ml · 2025-12-31</span>
          </div>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 999,
              background: 'rgba(15,157,88,.14)',
              font: "500 11px/1 'JetBrains Mono',monospace",
              letterSpacing: '.04em',
              color: '#0F9D58',
            }}
          >
            DADOS REAIS · API · FASE 14
          </span>
        </div>
      </div>
      <nav className="max-w-[1360px] mx-auto flex gap-1.5 overflow-x-auto scrollbar-none">
        {TABS.map((tab, i) => (
          <button
            key={tab.name}
            onClick={() => onSelectTab(i)}
            className="shrink-0 whitespace-nowrap transition-colors hover:bg-[#F9F9FF]/70"
            style={{
              appearance: 'none',
              border: 0,
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              alignItems: 'flex-start',
              padding: '12px 20px 14px',
              borderRadius: '12px 12px 0 0',
              fontFamily: 'Inter,sans-serif',
              textAlign: 'left',
              transition: 'background 160ms cubic-bezier(.2,0,0,1)',
              background: i === activeTab ? '#F9F9FF' : 'transparent',
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: '-.01em', color: i === activeTab ? NAVY : MUTED }}>
              {tab.name}
            </span>
            <span style={{ fontSize: 11, fontWeight: 500, color: SUB }}>{tab.sub}</span>
          </button>
        ))}
      </nav>
    </header>
  )
}
