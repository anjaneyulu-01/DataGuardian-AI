import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Database,
  FileText,
  Radar,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router'

import { RiskBadge } from './RiskBadge'
import { SourceTag } from './SourceTag'
import type { DataSource } from '@/services'
import type { ActivityEvent, Finding } from '@/types/domain'
import { cn } from '@/utils'
import { timeAgo } from '@/utils/format'

interface NotificationsPanelProps {
  open: boolean
  onClose: () => void
  activity: ActivityEvent[]
  findings: Finding[]
  source: DataSource
  reason?: string
}

const KIND_ICON: Record<ActivityEvent['kind'], LucideIcon> = {
  scan: Radar,
  finding: AlertTriangle,
  fix: CheckCircle2,
  docs: FileText,
  system: Database,
}

const KIND_TONE: Record<ActivityEvent['kind'], string> = {
  scan: 'border-brand/25 bg-brand/10 text-brand-strong',
  finding: 'border-warning/25 bg-warning/10 text-warning',
  fix: 'border-positive/25 bg-positive/10 text-positive',
  docs: 'border-accent/25 bg-accent/10 text-accent',
  system: 'border-line bg-raised text-muted',
}

/**
 * Notifications dropdown.
 *
 * Merges two streams into one reverse-chronological list: agent activity
 * (scans, fixes, documentation runs) and risk alerts (critical and high
 * findings). They are separate concepts in the data model but the same thing
 * to a user — "what changed that I should know about?"
 */
export function NotificationsPanel({
  open,
  onClose,
  activity,
  findings,
  source,
  reason,
}: NotificationsPanelProps) {
  const navigate = useNavigate()
  const panelRef = useRef<HTMLDivElement>(null)

  // Close on outside click and on Escape — expected of any dropdown.
  useEffect(() => {
    if (!open) return

    const onPointerDown = (event: MouseEvent) => {
      if (!panelRef.current?.contains(event.target as Node)) onClose()
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }

    // `capture` so the toggle button's own click does not immediately reopen.
    document.addEventListener('mousedown', onPointerDown, true)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown, true)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open, onClose])

  const alerts = findings.filter(
    (finding) => finding.severity === 'critical' || finding.severity === 'high',
  )

  // One list, newest first, so the panel reads chronologically.
  const items = [
    ...alerts.map((finding) => ({
      id: `alert-${finding.id}`,
      timestamp: finding.detectedAt,
      title: finding.title,
      detail: `${finding.assetName} · ${finding.downstreamCount} downstream`,
      icon: AlertTriangle,
      tone: KIND_TONE.finding,
      severity: finding.severity,
      target: '/risk',
    })),
    ...activity.map((event) => ({
      id: `activity-${event.id}`,
      timestamp: event.timestamp,
      title: event.title,
      detail: event.detail,
      icon: KIND_ICON[event.kind],
      tone: KIND_TONE[event.kind],
      severity: event.severity,
      target: event.kind === 'finding' ? '/risk' : '/',
    })),
  ].sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp))

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          ref={panelRef}
          initial={{ opacity: 0, y: -8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.98 }}
          transition={{ duration: 0.16, ease: 'easeOut' }}
          role="dialog"
          aria-label="Notifications"
          className="card absolute top-11 right-0 z-50 w-[min(22rem,calc(100vw-2rem))] overflow-hidden p-0 shadow-pop"
        >
          <div className="border-line flex items-center gap-2 border-b px-4 py-3">
            <Bell className="text-muted size-3.5" />
            <p className="text-ink text-[13px] font-semibold">Notifications</p>
            <SourceTag source={source} reason={reason} className="ml-1" />
            <button
              type="button"
              onClick={onClose}
              aria-label="Close notifications"
              className="text-faint hover:text-ink ml-auto transition-colors"
            >
              <X className="size-3.5" />
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 ? (
              <p className="text-muted px-4 py-8 text-center text-[12.5px]">
                Nothing to report.
              </p>
            ) : (
              items.slice(0, 12).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    navigate(item.target)
                    onClose()
                  }}
                  className="border-line hover:bg-raised/60 flex w-full items-start gap-3 border-b px-4 py-3 text-left transition-colors last:border-0"
                >
                  <span
                    className={cn(
                      'mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg border',
                      item.tone,
                    )}
                  >
                    <item.icon className="size-3.5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-1.5">
                      <span className="text-ink text-[12.5px] font-medium">
                        {item.title}
                      </span>
                      {item.severity ? (
                        <RiskBadge severity={item.severity} size="sm" />
                      ) : null}
                    </span>
                    <span className="text-muted mt-0.5 block text-[11.5px] leading-snug">
                      {item.detail}
                    </span>
                    <span className="text-faint mt-1 block text-[10.5px]">
                      {timeAgo(item.timestamp)}
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}

