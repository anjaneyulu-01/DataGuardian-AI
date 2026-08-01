import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
}

/** Friendly zero-data state, used instead of blank panels. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <span className="border-line bg-raised text-muted grid size-12 place-items-center rounded-2xl border">
        <Icon className="size-5" strokeWidth={1.75} />
      </span>
      <p className="text-ink mt-4 text-sm font-semibold">{title}</p>
      <p className="text-muted mt-1 max-w-sm text-[13px] leading-relaxed">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}
