import type { Severity } from '@/types/domain'
import { cn } from '@/utils'
import { SEVERITY } from '@/utils/severity'

interface RiskBadgeProps {
  severity: Severity
  /** Renders the numeric score alongside the label. */
  score?: number
  size?: 'sm' | 'md'
  className?: string
}

/**
 * Severity pill with an optional score.
 *
 * The single severity badge in the app. Everywhere a severity appears — a
 * table row, an evidence item, a notification, a lineage inspector — it
 * renders through this component, so the colour, label, and (optional) score
 * can never disagree between two surfaces.
 */
export function RiskBadge({ severity, score, size = 'md', className }: RiskBadgeProps) {
  const style = SEVERITY[severity]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-semibold tracking-wide uppercase',
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-[11px]',
        style.bg,
        style.text,
        className,
      )}
    >
      <span className={cn('rounded-full', size === 'sm' ? 'size-1' : 'size-1.5', style.dot)} />
      {style.label}
      {score !== undefined ? (
        <span className="opacity-70 tabular-nums">{score}</span>
      ) : null}
    </span>
  )
}
