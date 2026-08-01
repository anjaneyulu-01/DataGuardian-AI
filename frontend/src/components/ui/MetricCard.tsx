import type { LucideIcon } from 'lucide-react'
import { TrendingDown, TrendingUp } from 'lucide-react'

import { Card } from './Card'
import { useCountUp } from '@/hooks/useCountUp'
import { cn } from '@/utils'
import { formatDelta, formatNumber } from '@/utils/format'

interface MetricCardProps {
  label: string
  value: number
  icon: LucideIcon
  /** Rendered after the number, e.g. "%" or "/100". */
  suffix?: string
  /** Week-over-week change. */
  delta?: number
  /** When true, a NEGATIVE delta is the good direction (e.g. critical issues). */
  deltaInverted?: boolean
  tone?: 'default' | 'positive' | 'critical'
}

/** KPI tile with an animated value and a trend chip. */
export function MetricCard({
  label,
  value,
  icon: Icon,
  suffix,
  delta,
  deltaInverted,
  tone = 'default',
}: MetricCardProps) {
  const animated = useCountUp(value)
  const improving = delta !== undefined && (deltaInverted ? delta < 0 : delta > 0)

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-muted text-[12px] font-medium tracking-wide uppercase">
          {label}
        </p>
        <span
          className={cn(
            'grid size-8 shrink-0 place-items-center rounded-lg border',
            tone === 'critical'
              ? 'border-critical/25 bg-critical/10 text-critical'
              : tone === 'positive'
                ? 'border-positive/25 bg-positive/10 text-positive'
                : 'border-brand/25 bg-brand/10 text-brand-strong',
          )}
        >
          <Icon className="size-4" strokeWidth={2} />
        </span>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-ink text-[28px] leading-none font-semibold tracking-tight tabular-nums">
          {formatNumber(animated)}
          {suffix ? (
            <span className="text-muted ml-0.5 text-base font-medium">{suffix}</span>
          ) : null}
        </span>
      </div>

      {delta !== undefined ? (
        <p
          className={cn(
            'mt-2 inline-flex items-center gap-1 text-[12px] font-medium',
            improving ? 'text-positive' : 'text-critical',
          )}
        >
          {delta >= 0 ? (
            <TrendingUp className="size-3.5" />
          ) : (
            <TrendingDown className="size-3.5" />
          )}
          {formatDelta(delta)}
          <span className="text-faint font-normal">vs last week</span>
        </p>
      ) : null}
    </Card>
  )
}
