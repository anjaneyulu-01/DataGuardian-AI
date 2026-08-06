import { Check, CircleSlash, Info, X } from 'lucide-react'

import type { ApiTraceEntry } from '@/types/api'
import { cn } from '@/utils'

interface EvidenceCompletenessProps {
  trace: ApiTraceEntry[]
  degraded: boolean
}

/**
 * Which evidence sources backed this answer.
 *
 * This deliberately replaces a "confidence score". There is no deterministic
 * basis for a confidence percentage in this system — inventing one would be
 * exactly the fabrication the rule engine exists to avoid. What *is* known,
 * precisely, is which tools ran, which the planner skipped, and which failed.
 * That is a more useful signal anyway: "this assessment saw no lineage data"
 * tells a steward what to distrust, where "confidence: 82%" does not.
 *
 * The three states are kept distinct on purpose:
 *
 * * **Collected** — the tool ran and returned evidence.
 * * **Not required** — the planner decided this question did not need it.
 *   This is a feature, not a gap; it is the evidence that the agent plans.
 * * **Unavailable** — the tool ran and failed. This is a real gap and is the
 *   only state that weakens the answer.
 */

interface EvidenceSource {
  /** Trace node that supplies this evidence. */
  node: string
  label: string
  /** What the source contributes to a governance verdict. */
  purpose: string
}

const SOURCES: EvidenceSource[] = [
  {
    node: 'datasets',
    label: 'Schema & tags',
    purpose: 'Column names and classifications — the basis for PII detection',
  },
  {
    node: 'owners',
    label: 'Ownership',
    purpose: 'Who is accountable for each asset',
  },
  {
    node: 'lineage',
    label: 'Lineage',
    purpose: 'Downstream blast radius, which sets priority',
  },
  {
    node: 'statistics',
    label: 'Usage & profiling',
    purpose: 'Row counts and query activity',
  },
]

type SourceState = 'collected' | 'not-required' | 'unavailable'

const STATE_META: Record<
  SourceState,
  { label: string; icon: typeof Check; tone: string }
> = {
  collected: {
    label: 'Collected',
    icon: Check,
    tone: 'border-positive/30 bg-positive/10 text-positive',
  },
  'not-required': {
    label: 'Not required',
    icon: CircleSlash,
    tone: 'border-line bg-raised text-faint',
  },
  unavailable: {
    label: 'Unavailable',
    icon: X,
    tone: 'border-critical/30 bg-critical/10 text-critical',
  },
}

function resolveState(entry: ApiTraceEntry | undefined): SourceState {
  // A node absent from the trace was never scheduled by the planner, which is
  // the same decision as an explicit skip.
  if (!entry || entry.status === 'skipped') return 'not-required'
  if (entry.status === 'failed') return 'unavailable'
  return 'collected'
}

export function EvidenceCompleteness({ trace, degraded }: EvidenceCompletenessProps) {
  const byNode = new Map(trace.map((entry) => [entry.node, entry]))

  const rows = SOURCES.map((source) => {
    const entry = byNode.get(source.node)
    return { ...source, state: resolveState(entry), error: entry?.error ?? null }
  })

  const collected = rows.filter((r) => r.state === 'collected').length
  const unavailable = rows.filter((r) => r.state === 'unavailable').length

  return (
    <div className="border-line rounded-xl border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-ink text-[13px] font-semibold">Evidence completeness</p>
        <span
          className={cn(
            'rounded-md border px-2 py-0.5 text-[11px] font-medium tabular-nums',
            unavailable > 0
              ? 'border-critical/30 bg-critical/10 text-critical'
              : 'border-positive/30 bg-positive/10 text-positive',
          )}
        >
          {collected} of {SOURCES.length} sources
        </span>
      </div>

      <p className="text-muted mt-1.5 text-[12px] leading-relaxed">
        {unavailable > 0
          ? `${unavailable} evidence ${unavailable === 1 ? 'source' : 'sources'} could not be reached, so this assessment is incomplete.`
          : 'Sources marked "not required" were deliberately skipped by the planner for this question — not missing.'}
      </p>

      <ul className="mt-3 space-y-1.5">
        {rows.map((row) => {
          const meta = STATE_META[row.state]
          const Icon = meta.icon
          return (
            <li key={row.node} className="flex items-start gap-2.5">
              <span
                className={cn(
                  'mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border',
                  meta.tone,
                )}
              >
                <Icon className="size-3" strokeWidth={2.5} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-ink text-[12.5px] font-medium">
                    {row.label}
                  </span>
                  <span className="text-faint text-[10.5px] font-medium tracking-wide uppercase">
                    {meta.label}
                  </span>
                </div>
                <p className="text-muted mt-0.5 text-[11.5px] leading-relaxed">
                  {row.state === 'unavailable' && row.error
                    ? row.error
                    : row.purpose}
                </p>
              </div>
            </li>
          )
        })}
      </ul>

      {degraded ? (
        <p className="text-warning mt-3 flex items-start gap-1.5 text-[11.5px] leading-relaxed">
          <Info className="mt-0.5 size-3.5 shrink-0" />
          The agent reported this run as degraded. Findings that depend on the
          unavailable sources may be missing entirely.
        </p>
      ) : null}
    </div>
  )
}
