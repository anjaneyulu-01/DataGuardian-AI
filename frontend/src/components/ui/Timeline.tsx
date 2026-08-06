import { RiskBadge } from './RiskBadge'
import type { Severity } from '@/types/domain'
import { timeAgo } from '@/utils/format'

export interface TimelineItem {
  id: string
  timestamp: string
  title: string
  description: string
  severity?: Severity
}

interface TimelineProps {
  items: TimelineItem[]
}

/**
 * Compact timeline of dated entries. Where `ActivityFeed` narrates what the
 * agent did (with per-kind icons), `Timeline` presents findings or milestones
 * as minimal cards along a rail.
 */
export function Timeline({ items }: TimelineProps) {
  return (
    <ol className="border-line ml-1.5 space-y-4 border-l pl-5">
      {items.map((item) => (
        <li key={item.id} className="relative">
          <span
            aria-hidden
            className="border-canvas bg-brand absolute top-1.5 -left-[26.5px] size-2.5 rounded-full border-2"
          />
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-ink text-[13px] font-medium">{item.title}</p>
            {item.severity ? <RiskBadge severity={item.severity} /> : null}
            <span className="text-faint ml-auto text-[11px]">
              {timeAgo(item.timestamp)}
            </span>
          </div>
          <p className="text-muted mt-1 text-[12.5px] leading-relaxed">
            {item.description}
          </p>
        </li>
      ))}
    </ol>
  )
}
