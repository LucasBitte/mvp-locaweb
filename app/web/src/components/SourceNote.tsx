type SourceNoteProps = {
  kind: 'sem-fonte' | 'fixo'
  label?: string
}

/**
 * Badge de transparência sobre a origem de um valor exibido.
 * 'sem-fonte': o backend ainda não persiste esse dado (ex: ml_dev vazio) — nenhum número é mostrado.
 * 'fixo': o valor é real (auditoria/notebook), mas hardcoded no backend, ainda não lido ao vivo da tabela.
 */
export default function SourceNote({ kind, label }: SourceNoteProps) {
  if (kind === 'sem-fonte') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200">
        sem fonte{label ? ` · ${label}` : ''}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
      fixo · aguardando Fase 5{label ? ` · ${label}` : ''}
    </span>
  )
}
