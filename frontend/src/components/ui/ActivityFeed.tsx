import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Radar,
  Settings2,
  type LucideIcon,
} from 'lucide-react'

import { RiskBadge } from './RiskBadge'
import type { ActivityEvent } from '@/types/domain'
import { cn } from '@/utils'
import { timeAgo } from '@/utils/format'

const KIND_ICON: Record<ActivityEvent['kind'], LucideIcon> = {
  scan: Radar,
  finding: AlertTriangle,
  fix: CheckCircle2,
  docs: FileText,
  system: Settings2,
}

const KIND_TONE: Record<ActivityEvent['kind'], string> = {
  scan: 'text-brand-strong border-brand/25 bg-brand/10',
  finding: 'text-warning border-warning/25 bg-warning/10',
  fix: 'text-positive border-positive/25 bg-positive/10',
  docs: 'text-accent border-accent/25 bg-accent/10',
  system: 'text-muted border-line bg-raised',
}

interface ActivityFeedProps {
  events: ActivityEvent[]
}

/** Vertical timeline of agent activity — scans, findings, fixes, docs. */
export function ActivityFeed({ events }: ActivityFeedProps) {
  return (
    <ol className="relative space-y-0">
      {events.map((event, index) => {
        const Icon = KIND_ICON[event.kind]
        const isLast = index === events.length - 1

        return (
          <li key={event.id} className="relative flex gap-3.5 pb-5 last:pb-0">
            {/* Connector line. */}
            {!isLast ? (
              <span
                aria-hidden
                className="bg-line absolute top-9 left-[15px] h-[calc(100%-2rem)] w-px"
              />
            ) : null}

            <span
              className={cn(
                'z-10 grid size-8 shrink-0 place-items-center rounded-lg border',
                KIND_TONE[event.kind],
              )}
            >
              <Icon className="size-4" strokeWidth={2} />
            </span>

            <div className="min-w-0 pt-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-ink text-[13px] font-medium">{event.title}</p>
                {event.severity ? <RiskBadge severity={event.severity} /> : null}
              </div>
              <p className="text-muted mt-0.5 text-[12.5px]">{event.detail}</p>
              <p className="text-faint mt-1 text-[11px]">{timeAgo(event.timestamp)}</p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
