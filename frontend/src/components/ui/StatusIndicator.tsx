import { cn } from '@/utils'

export type ConnectionState = 'checking' | 'online' | 'offline' | 'unconfigured'

interface StatusIndicatorProps {
  label: string
  state: ConnectionState
  /** Extra context shown on hover, e.g. the version or the error. */
  detail?: string
  /** Hides the text label, leaving the dot. For dense layouts. */
  compact?: boolean
  className?: string
}

const TONE: Record<ConnectionState, { dot: string; text: string }> = {
  online: { dot: 'bg-positive', text: 'text-positive' },
  offline: { dot: 'bg-critical', text: 'text-critical' },
  // Amber rather than red: a missing API key is a setup step, not a fault.
  unconfigured: { dot: 'bg-warning', text: 'text-warning' },
  checking: { dot: 'bg-muted animate-pulse', text: 'text-muted' },
}

const LABEL: Record<ConnectionState, string> = {
  online: 'Connected',
  offline: 'Offline',
  unconfigured: 'Not configured',
  checking: 'Checking',
}

/** Connection state for a dependency. Used in the top bar and Settings. */
export function StatusIndicator({
  label,
  state,
  detail,
  compact,
  className,
}: StatusIndicatorProps) {
  const tone = TONE[state]

  return (
    <span
      title={detail ? `${label}: ${LABEL[state]} — ${detail}` : `${label}: ${LABEL[state]}`}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium',
        'border-line bg-surface/70',
        className,
      )}
    >
      <span className={cn('size-1.5 shrink-0 rounded-full', tone.dot)} />
      {!compact ? <span className="text-muted">{label}</span> : null}
      <span className="sr-only">{LABEL[state]}</span>
    </span>
  )
}
