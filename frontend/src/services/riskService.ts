/**
 * Risk Center data.
 *
 * Severity distribution and top-risk assets are computed from live dataset
 * metadata. The trend chart is demo-only until scan history exists — the same
 * honesty rule as the Overview.
 */

import { fetchGovernanceAssets } from './governanceService'
import { fetchRiskTrend } from './overviewService'
import { demoOnly, type Sourced } from './fallback'
import { enterpriseFindings as demoFindings } from '@/data/enterpriseCatalogue'
import type { Finding, GovernanceAsset, RiskTrendPoint, Severity } from '@/types/domain'

export type SeverityCounts = Record<Severity, number>

export interface RiskOverview {
  counts: SeverityCounts
  topAssets: GovernanceAsset[]
  totalAssets: number
}

/** Assets listed under "Top Risk Assets". */
const TOP_RISK_LIMIT = 6

export async function fetchRiskOverview(): Promise<Sourced<RiskOverview>> {
  const { data, source, reason } = await fetchGovernanceAssets({ count: 100 })

  const counts: SeverityCounts = { critical: 0, high: 0, medium: 0, low: 0 }
  for (const asset of data.assets) {
    counts[asset.severity] += 1
  }

  // Worst health first — the order a steward should work through.
  const topAssets = [...data.assets]
    .sort((a, b) => a.health - b.health)
    .slice(0, TOP_RISK_LIMIT)

  return {
    data: { counts, topAssets, totalAssets: data.total },
    source,
    reason,
  }
}

export async function fetchRiskTrendSeries(): Promise<Sourced<RiskTrendPoint[]>> {
  return fetchRiskTrend()
}

/**
 * Governance violations.
 *
 * Live findings come from the agent, which computes them per question rather
 * than maintaining a standing list. Until a persisted findings endpoint
 * exists, this is demo data — clearly labelled.
 */
export async function fetchViolations(): Promise<Sourced<Finding[]>> {
  return demoOnly(
    demoFindings,
    'A standing findings list needs persisted scan history; ask the AI Investigator for live findings.',
  )
}
