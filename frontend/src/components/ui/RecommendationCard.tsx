import { ArrowUpRight, Sparkles } from 'lucide-react'

import { Card } from './Card'
import { RiskBadge } from './RiskBadge'
import type { Recommendation } from '@/types/domain'

interface RecommendationCardProps {
  recommendation: Recommendation
  /** Sends the action back to the Investigator as a follow-up question. */
  onRun?: (recommendation: Recommendation) => void
  index?: number
}

/**
 * A corrective action proposed by the agent.
 *
 * The rationale is always shown, never truncated behind a toggle: a
 * recommendation without its reason is an instruction, and a steward is
 * entitled to judge whether the reason holds before acting on it.
 */
export function RecommendationCard({
  recommendation,
  onRun,
  index,
}: RecommendationCardProps) {
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        {index !== undefined ? (
          <span className="border-brand/25 bg-brand/10 text-brand-strong mt-0.5 grid size-6 shrink-0 place-items-center rounded-md border font-mono text-[11px] font-semibold tabular-nums">
            {index + 1}
          </span>
        ) : (
          <span className="border-brand/25 bg-brand/10 text-brand-strong mt-0.5 grid size-6 shrink-0 place-items-center rounded-md border">
            <Sparkles className="size-3" />
          </span>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-ink text-[13px] font-semibold">{recommendation.action}</p>
            <RiskBadge severity={recommendation.priority} size="sm" />
          </div>
          <p className="text-muted mt-1 text-[12.5px] leading-relaxed">
            {recommendation.rationale}
          </p>

          {onRun ? (
            <button
              type="button"
              onClick={() => onRun(recommendation)}
              className="text-brand-strong mt-2.5 inline-flex items-center gap-1 text-[12px] font-medium hover:underline"
            >
              Investigate this <ArrowUpRight className="size-3.5" />
            </button>
          ) : null}
        </div>
      </div>
    </Card>
  )
}
