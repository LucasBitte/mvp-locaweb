import { BG_SOFT, NAVY, SUB } from '../lib/theme'

/**
 * Faixa no topo de cada aba com a pergunta de negócio que aquela tela responde.
 * O texto vem de TABS (Header.tsx), fonte única de verdade das abas.
 */
export function ScreenQuestion({ pergunta }: { pergunta: string }) {
  return (
    <div style={{ background: BG_SOFT, borderRadius: 16, padding: '18px 24px', marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={{ font: '600 12px/1 Inter,sans-serif', textTransform: 'uppercase', letterSpacing: '.05em', color: SUB }}>
        Pergunta que esta tela responde
      </span>
      <span style={{ font: '600 18px/1.3 Manrope,sans-serif', color: NAVY, textWrap: 'pretty' }}>{pergunta}</span>
    </div>
  )
}
