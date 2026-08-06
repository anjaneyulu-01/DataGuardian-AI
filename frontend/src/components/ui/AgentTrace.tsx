import { AnimatePresence, motion } from 'framer-motion'
import { Check, ChevronDown, CircleSlash, Workflow, X } from 'lucide-react'
import { useState } from 'react'

import type { ApiTraceEntry } from '@/types/api'
import { cn } from '@/utils'

interface AgentTraceProps {
  trace: ApiTraceEntry[]
  toolsUsed: string[]
  durationMs: number
  provider: string
}

const NODE_LABELS: Record<string, string> = {
  planner: 'Planned',
  datasets: 'Fetched datasets',
  owners: 'Resolved owners',
  lineage: 'Traced lineage',
  statistics: 'Read statistics',
  risk: 'Scored risk',
  reasoning: 'Explained findings',
  recommendation: 'Derived actions',
  report: 'Formatted report',
}

/**
 * The agent's execution trace, collapsed by default.
 *
 * This is what distinguishes an agent from a chatbot in the UI: it shows
 * which tools ran, which were skipped, and how long each took. A user can see
 * that an ownership question genuinely did not touch lineage, rather than
 * taking that claim on trust.
 */
export function AgentTrace({ trace, toolsUsed, durationMs, provider }: AgentTraceProps) {
  const [open, setOpen] = useState(false)
  const failed = trace.filter((entry) => entry.status === 'failed').length

  return (
    <div className="border-line border-t">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        className="text-muted hover:text-ink flex w-full items-center gap-2 px-5 py-2.5 text-[11.5px] transition-colors"
      >
        <Workflow className="size-3.5 shrink-0" />
        <span className="font-medium">
          {toolsUsed.length} step{toolsUsed.length === 1 ? '' : 's'}
        </span>
        <span className="text-faint">·</span>
        <span className="tabular-nums">{Math.round(durationMs)}ms</span>
        {provider ? (
          <>
            <span className="text-faint">·</span>
            <span className="text-faint">{provider}</span>
          </>
        ) : null}
        {failed > 0 ? (
          <span className="text-critical ml-1 font-medium">
            {failed} failed
          </span>
        ) : null}
        <ChevronDown
          className={cn(
            'ml-auto size-3.5 shrink-0 transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.ol
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="overflow-hidden px-5 pb-3"
          >
            {trace.map((entry, index) => (
              <li
                key={`${entry.node}-${index}`}
                className="flex items-center gap-2.5 py-1 text-[12px]"
              >
                <span
                  className={cn(
                    'grid size-4 shrink-0 place-items-center rounded-full',
                    entry.status === 'ok' && 'bg-positive/15 text-positive',
                    entry.status === 'failed' && 'bg-critical/15 text-critical',
                    entry.status === 'skipped' && 'bg-raised text-faint',
                  )}
                >
                  {entry.status === 'ok' ? (
                    <Check className="size-2.5" />
                  ) : entry.status === 'failed' ? (
                    <X className="size-2.5" />
                  ) : (
                    <CircleSlash className="size-2.5" />
                  )}
                </span>

                <span className="text-ink-secondary">
                  {NODE_LABELS[entry.node] ?? entry.node}
                </span>
                <span className="text-faint ml-auto tabular-nums">
                  {Math.round(entry.duration_ms)}ms
                </span>
              </li>
            ))}

            {trace.some((entry) => entry.error) ? (
              <li className="text-critical mt-2 text-[11.5px]">
                {trace.find((entry) => entry.error)?.error}
              </li>
            ) : null}
          </motion.ol>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
