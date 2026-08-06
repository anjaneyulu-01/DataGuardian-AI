import { ArrowRight, GitBranch } from 'lucide-react'

import { Card } from './Card'
import { RiskBadge } from './RiskBadge'
import type { Finding } from '@/types/domain'
import { cn } from '@/utils'

interface IssueCardProps {
  finding: Finding
  /** Opens the asset (Lineage / Governance). */
  onInspect?: (finding: Finding) => void
  /** Runs the recommendation through the Investigator. */
  onAction?: (action: string, finding: Finding) => void
  compact?: boolean
}

/**
 * One governance finding.
 *
 * Distinct from `RiskCard` (the Overview's detailed variant): this is the
 * denser form used in lists, and it leads with the RULE that fired. Naming
 * the rule is what makes a finding auditable rather than an opinion.
 */
export function IssueCard({ finding, onInspect, onAction, compact }: IssueCardProps) {
  return (
    <Card
      interactive={Boolean(onInspect)}
      onClick={onInspect ? () => onInspect(finding) : undefined}
      className={cn('p-4', compact && 'p-3.5')}
    >
      <div className="flex flex-wrap items-center gap-2">
        <RiskBadge severity={finding.severity} size="sm" />
        <span className="text-ink text-[13px] font-semibold">{finding.assetName}</span>
        {finding.downstreamCount > 0 ? (
          <span className="text-muted inline-flex items-center gap-1 text-[11.5px]">
            <GitBranch className="size-3" />
            {finding.downstreamCount}
          </span>
        ) : null}
        {onInspect ? (
          <ArrowRight className="text-faint ml-auto size-3.5 shrink-0" />
        ) : null}
      </div>

      <p className="text-ink-secondary mt-2 text-[13px] font-medium">{finding.title}</p>

      {!compact ? (
        <p className="text-muted mt-1 text-[12.5px] leading-relaxed">{finding.summary}</p>
      ) : null}

      {onAction && finding.recommendations.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {finding.recommendations.slice(0, 2).map((recommendation) => (
            <button
              key={recommendation}
              type="button"
              onClick={(event) => {
                // The card itself may be clickable; do not trigger both.
                event.stopPropagation()
                onAction(recommendation, finding)
              }}
              className="border-line bg-raised text-ink-secondary hover:border-brand/40 hover:text-ink rounded-lg border px-2.5 py-1 text-[11.5px] font-medium transition-colors"
            >
              {recommendation}
            </button>
          ))}
        </div>
      ) : null}
    </Card>
  )
}
