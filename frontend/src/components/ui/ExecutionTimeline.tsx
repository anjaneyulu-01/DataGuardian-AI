import { motion } from 'framer-motion'
import {
  Brain,
  CircleSlash,
  Database,
  GitBranch,
  Lightbulb,
  ScrollText,
  ShieldAlert,
  Sparkles,
  Users,
  Workflow,
  X,
  type LucideIcon,
} from 'lucide-react'

import type { ApiTraceEntry } from '@/types/api'
import { cn } from '@/utils'

interface ExecutionTimelineProps {
  trace: ApiTraceEntry[]
  durationMs: number
  provider: string
  /** Renders the compact horizontal strip instead of the full timeline. */
  compact?: boolean
}

interface StageMeta {
  label: string
  /** What the stage did, in one line. */
  purpose: string
  icon: LucideIcon
  /** Deterministic stages are the auditable ones; LLM stages are generative. */
  kind: 'plan' | 'tool' | 'deterministic' | 'llm'
}

/**
 * The agent's pipeline, in execution order.
 *
 * Mirrors the graph in `backend/app/agents/workflow.py`. The `kind` field is
 * the important one: it lets the UI colour deterministic stages differently
 * from generative ones, which is the visual expression of the product's core
 * claim — the numbers are computed, only the prose is written.
 */
const STAGES: Record<string, StageMeta> = {
  planner: {
    label: 'Planner',
    purpose: 'Classified the question and chose which tools to run',
    icon: Workflow,
    kind: 'plan',
  },
  datasets: {
    label: 'Dataset Tool',
    purpose: 'Read dataset metadata from DataHub',
    icon: Database,
    kind: 'tool',
  },
  owners: {
    label: 'Owner Tool',
    purpose: 'Resolved ownership records',
    icon: Users,
    kind: 'tool',
  },
  lineage: {
    label: 'Lineage Tool',
    purpose: 'Traced upstream and downstream impact',
    icon: GitBranch,
    kind: 'tool',
  },
  statistics: {
    label: 'Statistics Tool',
    purpose: 'Collected profiling and usage figures',
    icon: ScrollText,
    kind: 'tool',
  },
  risk: {
    label: 'Risk Engine',
    purpose: 'Applied deterministic governance rules — no LLM involved',
    icon: ShieldAlert,
    kind: 'deterministic',
  },
  reasoning: {
    label: 'LLM Reasoning',
    purpose: 'Explained the findings the rule engine produced',
    icon: Brain,
    kind: 'llm',
  },
  recommendation: {
    label: 'Recommendations',
    purpose: 'Derived corrective actions, bounded by the findings',
    icon: Lightbulb,
    kind: 'llm',
  },
  report: {
    label: 'Report',
    purpose: 'Formatted the executive governance report',
    icon: Sparkles,
    kind: 'llm',
  },
}

const KIND_TONE: Record<StageMeta['kind'], string> = {
  plan: 'border-brand/30 bg-brand/10 text-brand-strong',
  tool: 'border-accent/30 bg-accent/10 text-accent',
  deterministic: 'border-positive/30 bg-positive/10 text-positive',
  llm: 'border-warning/30 bg-warning/10 text-warning',
}

const KIND_LABEL: Record<StageMeta['kind'], string> = {
  plan: 'Planning',
  tool: 'Tool',
  deterministic: 'Deterministic',
  llm: 'Generative',
}

/**
 * Visual execution pipeline for one agent run.
 *
 * Renders every stage the graph actually executed, in order, with its
 * duration and whether it succeeded, was skipped, or failed. Skipped stages
 * are shown rather than omitted — "it did not call the lineage tool" is the
 * evidence that the agent plans, and hiding it would lose the point.
 */
export function ExecutionTimeline({
  trace,
  durationMs,
  provider,
  compact,
}: ExecutionTimelineProps) {
  if (trace.length === 0) return null

  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-1.5">
        {trace.map((entry, index) => {
          const stage = STAGES[entry.node]
          const Icon = stage?.icon ?? Workflow
          return (
            <motion.span
              key={`${entry.node}-${index}`}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05, duration: 0.2 }}
              title={`${stage?.label ?? entry.node} · ${Math.round(entry.duration_ms)}ms`}
              className={cn(
                'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10.5px] font-medium',
                entry.status === 'failed'
                  ? 'border-critical/30 bg-critical/10 text-critical'
                  : entry.status === 'skipped'
                    ? 'border-line bg-raised text-faint'
                    : KIND_TONE[stage?.kind ?? 'tool'],
              )}
            >
              <Icon className="size-3" />
              {stage?.label ?? entry.node}
            </motion.span>
          )
        })}
      </div>
    )
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <p className="text-faint text-[11px] font-semibold tracking-widest uppercase">
          Execution Pipeline
        </p>
        <span className="text-muted text-[11.5px] tabular-nums">
          {trace.length} stages · {Math.round(durationMs)}ms
          {provider ? ` · ${provider}` : ''}
        </span>
        <div className="text-faint ml-auto hidden items-center gap-2.5 text-[10.5px] sm:flex">
          {(['tool', 'deterministic', 'llm'] as const).map((kind) => (
            <span key={kind} className="inline-flex items-center gap-1">
              <span
                className={cn('size-2 rounded-sm border', KIND_TONE[kind])}
                aria-hidden
              />
              {KIND_LABEL[kind]}
            </span>
          ))}
        </div>
      </div>

      <ol className="relative">
        {trace.map((entry, index) => {
          const stage = STAGES[entry.node]
          const Icon = stage?.icon ?? Workflow
          const isLast = index === trace.length - 1
          const failed = entry.status === 'failed'
          const skipped = entry.status === 'skipped'

          return (
            <motion.li
              key={`${entry.node}-${index}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.06, duration: 0.28, ease: 'easeOut' }}
              className="relative flex gap-3.5 pb-4 last:pb-0"
            >
              {/* Connector between stages. */}
              {!isLast ? (
                <span
                  aria-hidden
                  className="bg-line absolute top-9 left-[17px] h-[calc(100%-2rem)] w-px"
                />
              ) : null}

              <span
                className={cn(
                  'z-10 grid size-9 shrink-0 place-items-center rounded-lg border',
                  failed
                    ? 'border-critical/30 bg-critical/10 text-critical'
                    : skipped
                      ? 'border-line bg-raised text-faint'
                      : KIND_TONE[stage?.kind ?? 'tool'],
                )}
              >
                {failed ? (
                  <X className="size-4" />
                ) : skipped ? (
                  <CircleSlash className="size-4" />
                ) : (
                  <Icon className="size-4" strokeWidth={2} />
                )}
              </span>

              <div className="min-w-0 flex-1 pt-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p
                    className={cn(
                      'text-[13px] font-semibold',
                      skipped ? 'text-faint' : 'text-ink',
                    )}
                  >
                    {stage?.label ?? entry.node}
                  </p>
                  {stage ? (
                    <span className="text-faint text-[10px] font-medium tracking-wide uppercase">
                      {KIND_LABEL[stage.kind]}
                    </span>
                  ) : null}
                  <span className="text-faint ml-auto text-[11.5px] tabular-nums">
                    {Math.round(entry.duration_ms)}ms
                  </span>
                </div>

                <p
                  className={cn(
                    'mt-0.5 text-[12px] leading-relaxed',
                    failed ? 'text-critical' : 'text-muted',
                  )}
                >
                  {failed
                    ? entry.error
                    : skipped
                      ? 'Skipped — the planner decided this was not needed'
                      : (stage?.purpose ?? entry.detail)}
                </p>
              </div>
            </motion.li>
          )
        })}
      </ol>
    </div>
  )
}
