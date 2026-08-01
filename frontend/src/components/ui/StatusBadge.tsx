import type { Severity } from '@/types/domain'
import { cn } from '@/utils'
import { SEVERITY } from '@/utils/severity'

interface StatusBadgeProps {
  severity: Severity
  /** Compact renders the dot only — used inside dense tables. */
  compact?: boolean
  className?: string
}

/** Severity pill. The only way severities are rendered anywhere in the app. */
export function StatusBadge({ severity, compact, className }: StatusBadgeProps) {
  const style = SEVERITY[severity]

  if (compact) {
    return (
      <span
        title={style.label}
        className={cn('inline-block size-2 rounded-full', style.dot, className)}
      />
    )
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase',
        style.bg,
        style.text,
        className,
      )}
    >
      <span className={cn('size-1.5 rounded-full', style.dot)} />
      {style.label}
    </span>
  )
}
