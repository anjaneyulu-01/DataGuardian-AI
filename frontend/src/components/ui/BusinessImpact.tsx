import { ArrowRight, Building2, GitBranch, TriangleAlert } from 'lucide-react'

import { RiskBadge } from './RiskBadge'
import type { ApiAgentResult } from '@/types/api'
import type { Severity } from '@/types/domain'

interface BusinessImpactProps {
  result: ApiAgentResult
}

/**
 * The "so what" for a finding set, promoted to a primary surface.
 *
 * `business_impact` and `next_steps` are already computed by the agent and
 * were previously collapsed into a fallback string. A governance finding
 * without its consequence is a backlog ticket; with it, it is a priority.
 *
 * Every figure here is read from the response — none is derived, estimated,
 * or extrapolated. Where the agent supplied no impact statement, the section
 * does not render at all rather than filling the space with a placeholder.
 */
export function BusinessImpact({ result }: BusinessImpactProps) {
  const statement = result.business_impact?.trim()
  const steps = result.next_steps ?? []

  // Blast radius, only where lineage actually ran and reported it.
  const downstream = result.evidence.reduce((total, item) => {
    const count = item.downstream_count
    return typeof count === 'number' ? total + count : total
  }, 0)

  const affectedAssets = result.evidence.filter((item) => {
    const rules = item.triggered_rules
    return Array.isArray(rules) && rules.length > 0
  }).length

  if (!statement && steps.length === 0 && affectedAssets === 0) return null

  return (
    <div className="border-line bg-raised/40 rounded-xl border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Building2 className="text-brand-strong size-4" />
        <p className="text-ink text-[13px] font-semibold">Business impact</p>
        <span className="ml-auto">
          <RiskBadge severity={result.risk_level as Severity} size="sm" />
        </span>
      </div>

      {statement ? (
        <p className="text-ink-secondary mt-2 text-[13px] leading-relaxed">
          {statement}
        </p>
      ) : null}

      {/* Measured figures only. Each tile is omitted when its source did not
          run, rather than rendering a zero that reads as "none found". */}
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {affectedAssets > 0 ? (
          <ImpactTile
            icon={<TriangleAlert className="size-3.5" />}
            value={affectedAssets}
            label={affectedAssets === 1 ? 'Asset affected' : 'Assets affected'}
          />
        ) : null}
        {downstream > 0 ? (
          <ImpactTile
            icon={<GitBranch className="size-3.5" />}
            value={downstream}
            label="Downstream consumers"
          />
        ) : null}
        <ImpactTile
          icon={<TriangleAlert className="size-3.5" />}
          value={result.findings.length}
          label={result.findings.length === 1 ? 'Rule triggered' : 'Rules triggered'}
        />
      </div>

      {steps.length > 0 ? (
        <div className="mt-3.5">
          <p className="text-faint text-[10px] font-semibold tracking-widest uppercase">
            Next steps
          </p>
          <ol className="mt-1.5 space-y-1.5">
            {steps.map((step, index) => (
              <li
                key={step}
                className="text-ink-secondary flex gap-2 text-[12.5px] leading-relaxed"
              >
                <ArrowRight className="text-faint mt-0.5 size-3.5 shrink-0" />
                <span>
                  <span className="text-faint mr-1 font-mono text-[11px] tabular-nums">
                    {index + 1}.
                  </span>
                  {step}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  )
}

function ImpactTile({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode
  value: number
  label: string
}) {
  return (
    <div className="border-line bg-surface rounded-lg border px-3 py-2.5">
      <span className="text-faint flex items-center gap-1.5">{icon}</span>
      <p className="text-ink mt-1 text-lg font-semibold tabular-nums">{value}</p>
      <p className="text-muted text-[11px] leading-tight">{label}</p>
    </div>
  )
}
