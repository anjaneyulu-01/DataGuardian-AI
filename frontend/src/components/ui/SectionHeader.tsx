import type { ReactNode } from 'react'

interface SectionHeaderProps {
  title: string
  description?: string
  /** Right-aligned slot for actions (filters, "view all" links…). */
  action?: ReactNode
}

/** Heading for a section within a page. */
export function SectionHeader({ title, description, action }: SectionHeaderProps) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <h2 className="text-ink text-[15px] font-semibold tracking-tight">{title}</h2>
        {description ? (
          <p className="text-muted mt-0.5 text-[13px]">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}
