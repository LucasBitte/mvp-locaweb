import { MUTED, RED, SUB } from '../lib/theme'

const wrap = { padding: '48px 0', display: 'flex', justifyContent: 'center' as const }

export function Loading() {
  return (
    <div style={wrap}>
      <span style={{ font: '500 13px/1 Inter,sans-serif', color: SUB }}>Carregando dado real da API…</span>
    </div>
  )
}

export function ErrorState({ error }: { error: string }) {
  return (
    <div style={wrap}>
      <div style={{ maxWidth: 560, textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <span style={{ font: '600 14px/1.3 Manrope,sans-serif', color: RED }}>Não foi possível carregar esta tela</span>
        <span style={{ font: '400 12px/1.5 Inter,sans-serif', color: MUTED }}>
          {error} — confirme se a API está rodando (<code>./venv/bin/uvicorn app.api.main:app --reload</code> a partir da
          raiz do repo) e se <code>VITE_API_BASE_URL</code> aponta para ela.
        </span>
      </div>
    </div>
  )
}
