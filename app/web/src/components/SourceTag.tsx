import type { CSSProperties, ReactNode } from 'react'
import { MUTED } from '../lib/theme'

interface SourceTagProps {
  children: ReactNode
  variant?: 'modelo' | 'regra' | 'historico' | 'calculado'
  visible: boolean
}

const VARIANT_BG: Record<NonNullable<SourceTagProps['variant']>, string> = {
  modelo: '#F0F3FF',
  regra: 'rgba(10,22,40,.06)',
  historico: 'rgba(10,22,40,.06)',
  calculado: 'rgba(10,22,40,.06)',
}

/** Selo "MODELO · X" / "REGRA · X" que aparece em quase todo card — mostra a
 * origem do dado (governança: nunca deixar implícito se é ML ou regra). */
export function SourceTag({ children, variant = 'regra', visible }: SourceTagProps) {
  const style: CSSProperties = {
    alignSelf: 'flex-start',
    padding: '5px 10px',
    borderRadius: 999,
    background: VARIANT_BG[variant],
    borderBottom: variant === 'modelo' ? '2px solid #00C8F0' : undefined,
    font: "500 10px/1 'JetBrains Mono', monospace",
    letterSpacing: '.06em',
    color: MUTED,
    overflowWrap: 'anywhere',
    display: visible ? 'inline-flex' : 'none',
  }
  return <span style={style}>{children}</span>
}
