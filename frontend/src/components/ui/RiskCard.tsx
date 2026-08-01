import { GitBranch, Sparkles } from 'lucide-react'

import { Card } from './Card'
import { StatusBadge } from './StatusBadge'
import type { Finding } from '@/types/domain'
import { timeAgo } from '@/utils/format'

interface RiskCardProps {
  finding: Finding
  /** Called with the recommendation label when one of the actions is clicked. */
  onAction?: (recommendation: string, finding: Finding) => void
}

/** A single governance finding with its recommended actions. */
export function RiskCard({ finding, onAction }: RiskCardProps) {
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-ink text-sm font-semibold">{finding.assetName}</span>
        <StatusBadge severity={finding.severity} />
        <span className="text-muted inline-flex items-center gap-1 text-[12px]">
          <GitBranch className="size-3.5" />
          {finding.downstreamCount} downstream
        </span>
        <span className="text-faint ml-auto text-[12px]">
          {timeAgo(finding.detectedAt)}
        </span>
      </div>

      <p className="text-ink-secondary mt-2.5 text-sm font-medium">{finding.title}</p>
      <p className="text-muted mt-1 text-[13px] leading-relaxed">{finding.summary}</p>

      <div className="border-line mt-4 flex flex-wrap items-center gap-2 border-t pt-3.5">
        <span className="text-faint inline-flex items-center gap-1 text-[11px] font-medium tracking-wide uppercase">
          <Sparkles className="size-3" /> Recommended
        </span>
        {finding.recommendations.map((rec) => (
          <button
            key={rec}
            type="button"
            onClick={() => onAction?.(rec, finding)}
            className="border-line bg-raised text-ink-secondary hover:border-brand/40 hover:text-ink rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors"
          >
            {rec}
          </button>
        ))}
      </div>
    </Card>
  )
}
