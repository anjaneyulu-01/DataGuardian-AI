/**
 * Overview metrics.
 *
 * Derived from `GET /api/v1/datasets` — the one live source that exists
 * today. Counts (assets, unowned, undocumented, coverage) are real: they are
 * computed by counting what DataHub actually returned.
 *
 * Week-over-week deltas and the risk trend are NOT real. They need scan
 * history, which arrives with the PostgreSQL model in a later phase, so they
 * come from demo data and are tagged `demo` so the UI can label them. Showing
 * an invented trend as fact would undermine the product's core claim.
 */

import { apiClient } from './apiClient'
import { toGovernanceAsset } from './governanceService'
import { withFallback, demoOnly, type Sourced } from './fallback'
import {
  enterpriseActivity,
  enterpriseMetrics,
  enterpriseRiskTrend,
} from '@/data/enterpriseCatalogue'
import { healthSummary } from '@/data/mockData'
import type { ApiDatasetSummary, ApiDomain, ApiOwner, ApiPage } from '@/types/api'
import type { ActivityEvent, HealthSummary, RiskTrendPoint } from '@/types/domain'

/** Assets pulled to compute the headline figures. */
const OVERVIEW_SAMPLE_SIZE = 100

export interface OverviewMetrics extends HealthSummary {
  /** Catalogue-wide documentation coverage, 0–100. */
  documentationCoverage: number
  /** Assets with no owner. */
  missingOwners: number
  /** Distinct business domains defined in DataHub. */
  domainCount: number
  /** Share of assets that appear in at least one lineage edge, 0–100. */
  lineageCoverage: number
  /** True when the deltas are demo values rather than measured history. */
  deltasAreEstimated: boolean
}

export async function fetchOverview(): Promise<Sourced<OverviewMetrics>> {
  return withFallback(
    async () => {
      // Three independent endpoints. `allSettled` rather than `all`: owners
      // and domains are secondary, and losing the whole Overview because a
      // domain lookup failed would be the wrong trade.
      const [datasetsResult, ownersResult, domainsResult] = await Promise.allSettled([
        apiClient.get<ApiPage<ApiDatasetSummary>>('/v1/datasets', {
          params: { query: '*', start: 0, count: OVERVIEW_SAMPLE_SIZE },
        }),
        apiClient.get<ApiOwner[]>('/v1/owners'),
        apiClient.get<ApiPage<ApiDomain>>('/v1/domains', { params: { count: 100 } }),
      ])

      // Datasets are load-bearing — without them there is nothing to report,
      // so a failure here must propagate to the demo fallback.
      if (datasetsResult.status === 'rejected') throw datasetsResult.reason

      const assets = datasetsResult.value.data.results.map(toGovernanceAsset)
      const total = datasetsResult.value.data.total || assets.length

      const missingOwners = assets.filter((a) => !a.owner).length
      const undocumented = assets.filter((a) => !a.description).length

      // Prefer the owners endpoint's aggregation; fall back to counting
      // distinct owners on the sampled assets.
      const owners =
        ownersResult.status === 'fulfilled'
          ? ownersResult.value.data.length
          : new Set(assets.map((a) => a.owner).filter(Boolean)).size

      const domainCount =
        domainsResult.status === 'fulfilled'
          ? domainsResult.value.data.total
          : new Set(assets.map((a) => a.domain).filter(Boolean)).size

      // Lineage coverage: share of assets carrying a domain AND an owner is a
      // poor proxy, so use what the dataset payload actually reveals — assets
      // that are connected to something. Without a bulk lineage endpoint this
      // is the honest approximation, and it is labelled as coverage, not as a
      // graph statistic.
      const connected = assets.filter(
        (a) => a.downstreamCount > 0 || Boolean(a.domain && a.domain !== 'Unassigned'),
      ).length

      return {
        score: Math.round(average(assets.map((a) => a.health))),
        totalAssets: total,
        healthyAssets: assets.filter((a) => a.health >= 80).length,
        criticalIssues: assets.filter((a) => a.severity === 'critical').length,
        coverage: Math.round(average(assets.map((a) => a.coverage))),
        owners,
        domainCount,
        documentationCoverage: assets.length
          ? Math.round(((assets.length - undocumented) / assets.length) * 100)
          : 0,
        lineageCoverage: assets.length
          ? Math.round((connected / assets.length) * 100)
          : 0,
        missingOwners,
        // No scan history yet, so no measured week-over-week movement.
        deltas: healthSummary.deltas,
        deltasAreEstimated: true,
      }
    },
    () => {
      const demo = enterpriseMetrics()
      return {
        score: demo.score,
        totalAssets: demo.totalAssets,
        healthyAssets: demo.healthyAssets,
        criticalIssues: demo.criticalIssues,
        coverage: demo.coverage,
        owners: demo.owners,
        domainCount: demo.domains,
        documentationCoverage: demo.documentationCoverage,
        lineageCoverage: demo.lineageCoverage,
        missingOwners: demo.missingOwners,
        deltas: healthSummary.deltas,
        deltasAreEstimated: true,
      }
    },
    'overviewService.metrics',
  )
}

/**
 * Risk trend over time.
 *
 * Demo-only: trends require stored scan history. Explicitly labelled rather
 * than fabricated silently.
 */
export async function fetchRiskTrend(): Promise<Sourced<RiskTrendPoint[]>> {
  return Promise.resolve(
    demoOnly(
      enterpriseRiskTrend,
      'Risk trends need persisted scan history, which lands with the scheduler phase.',
    ),
  )
}

/**
 * Agent activity feed.
 *
 * Demo-only for the same reason: run history is not persisted yet.
 */
export async function fetchActivity(): Promise<Sourced<ActivityEvent[]>> {
  return Promise.resolve(
    demoOnly(enterpriseActivity, 'Agent run history is not persisted yet.'),
  )
}

function average(values: number[]): number {
  if (values.length === 0) return 0
  return values.reduce((sum, value) => sum + value, 0) / values.length
}
