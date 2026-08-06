import { Database, FlaskConical } from 'lucide-react'

import type { DataSource } from '@/services'
import { cn } from '@/utils'

interface SourceTagProps {
  source: DataSource
  /** Why demo data is being shown. Surfaced as a tooltip. */
  reason?: string
  className?: string
}

/**
 * Labels a panel as live or demo data.
 *
 * Non-negotiable in a governance product: presenting invented figures as if
 * they came from a real catalogue is precisely the failure this tool exists
 * to catch. Every panel that can fall back to demo data renders one of these.
 *
 * Live data gets a quiet tag; demo data gets an amber one that is meant to be
 * noticed.
 */
export function SourceTag({ source, reason, className }: SourceTagProps) {
  const isLive = source === 'live'
  const Icon = isLive ? Database : FlaskConical

  return (
    <span
      title={
        reason ??
        (isLive
          ? 'Live data from the DataGuardian API'
          : 'Illustrative data — not from your catalogue')
      }
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase',
        isLive
          ? 'border-positive/25 bg-positive/10 text-positive'
          : 'border-warning/25 bg-warning/10 text-warning',
        className,
      )}
    >
      <Icon className="size-2.5" />
      {isLive ? 'Live' : 'Demo'}
    </span>
  )
}
