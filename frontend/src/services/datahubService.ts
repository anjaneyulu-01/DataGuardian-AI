/**
 * The DataHub integration report.
 *
 * Every figure here is read from a live endpoint — there is no derived,
 * smoothed, or estimated value in this file. That matters more here than
 * anywhere else in the app: this is the page that claims "we really use
 * DataHub", so a single invented number would discredit the claim it exists
 * to support.
 *
 * Where a figure is genuinely unavailable it is returned as `null` and the UI
 * renders "not available" rather than a zero. A zero asserts "we looked and
 * found none"; null says "we could not measure this", and conflating them is
 * how dashboards start lying.
 */

import { apiClient } from './apiClient'
import { demoOnly, withFallback, type Sourced } from './fallback'
import { enterpriseAssets, enterpriseDomains, enterpriseOwners } from '@/data/enterpriseCatalogue'
import type {
  ApiDatasetSummary,
  ApiDomain,
  ApiOwner,
  ApiPage,
  CacheStats,
  DataHubHealth,
} from '@/types/api'

/** Assets sampled to compute coverage percentages. */
const COVERAGE_SAMPLE = 100

export interface EntityBreakdown {
  label: string
  /** Null when the count could not be measured. */
  count: number | null
  detail: string
}

export interface CoverageMetric {
  label: string
  /** Percentage 0–100, or null when not measurable. */
  percent: number | null
  covered: number
  total: number
  detail: string
}

export interface DataHubReport {
  health: DataHubHealth
  cache: CacheStats | null
  entities: EntityBreakdown[]
  coverage: CoverageMetric[]
  /** Platforms observed on the sampled assets. */
  platforms: { name: string; count: number }[]
  /** How many assets the coverage figures were computed over. */
  sampleSize: number
  /** Total assets DataHub reports, which may exceed the sample. */
  totalAssets: number | null
}

export async function fetchDataHubReport(): Promise<Sourced<DataHubReport>> {
  return withFallback<DataHubReport>(
    async () => {
      const [healthResult, datasetsResult, ownersResult, domainsResult] =
        await Promise.allSettled([
          apiClient.get<DataHubHealth & { cache?: CacheStats | null }>(
            '/v1/health/datahub',
          ),
          apiClient.get<ApiPage<ApiDatasetSummary>>('/v1/datasets', {
            params: { query: '*', start: 0, count: COVERAGE_SAMPLE },
          }),
          apiClient.get<ApiOwner[]>('/v1/owners'),
          apiClient.get<ApiPage<ApiDomain>>('/v1/domains', { params: { count: 100 } }),
        ])

      // Health is load-bearing: without it there is no connection to report,
      // and falling back to demo is the honest outcome.
      if (healthResult.status === 'rejected') throw healthResult.reason

      const health = healthResult.value.data
      const cache = health.cache ?? null

      const datasets =
        datasetsResult.status === 'fulfilled'
          ? datasetsResult.value.data.results
          : []
      const totalAssets =
        datasetsResult.status === 'fulfilled'
          ? datasetsResult.value.data.total
          : null

      const ownerCount =
        ownersResult.status === 'fulfilled' ? ownersResult.value.data.length : null
      const domainCount =
        domainsResult.status === 'fulfilled' ? domainsResult.value.data.total : null

      const sampleSize = datasets.length
      const owned = datasets.filter((d) => (d.owners?.length ?? 0) > 0).length
      const documented = datasets.filter((d) => Boolean(d.description?.trim())).length
      const tagged = datasets.filter((d) => (d.tags?.length ?? 0) > 0).length
      const domained = datasets.filter((d) => Boolean(d.domain)).length

      const platformCounts = new Map<string, number>()
      for (const dataset of datasets) {
        const name = dataset.platform?.name
        if (name) platformCounts.set(name, (platformCounts.get(name) ?? 0) + 1)
      }

      return {
        health,
        cache,
        entities: [
          {
            label: 'Datasets',
            count: totalAssets,
            detail: 'Total the catalogue reports for a wildcard search',
          },
          {
            label: 'Owners',
            count: ownerCount,
            detail: 'Distinct users and groups across the catalogue',
          },
          {
            label: 'Domains',
            count: domainCount,
            detail: 'Business domains defined in DataHub',
          },
          {
            label: 'Platforms',
            count: platformCounts.size || null,
            detail: `Source systems observed in the ${sampleSize}-asset sample`,
          },
        ],
        coverage: [
          coverage('Ownership', owned, sampleSize, 'Assets with at least one owner'),
          coverage(
            'Documentation',
            documented,
            sampleSize,
            'Assets with a non-empty description',
          ),
          coverage('Tags', tagged, sampleSize, 'Assets carrying at least one tag'),
          coverage(
            'Domain assignment',
            domained,
            sampleSize,
            'Assets assigned to a business domain',
          ),
        ],
        platforms: [...platformCounts.entries()]
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count),
        sampleSize,
        totalAssets,
      }
    },
    () => demoReport(),
    'datahubService.report',
  )
}

function coverage(
  label: string,
  covered: number,
  total: number,
  detail: string,
): CoverageMetric {
  return {
    label,
    // Null rather than 0 when there is nothing to divide by: "0% documented"
    // on an empty sample is a false statement about the catalogue.
    percent: total > 0 ? Math.round((covered / total) * 100) : null,
    covered,
    total,
    detail,
  }
}

/**
 * The Demo Mode equivalent, computed from the same deterministic catalogue
 * the rest of Demo Mode uses, so the numbers reconcile across pages.
 */
function demoReport(): DataHubReport {
  const assets = enterpriseAssets
  const total = assets.length
  const owned = assets.filter((a) => Boolean(a.owner)).length
  const documented = assets.filter((a) => Boolean(a.description)).length
  const tagged = assets.filter((a) => a.tags.length > 0).length
  const domained = assets.filter((a) => Boolean(a.domain)).length

  const platformCounts = new Map<string, number>()
  for (const asset of assets) {
    platformCounts.set(asset.platform, (platformCounts.get(asset.platform) ?? 0) + 1)
  }

  return {
    health: {
      reachable: false,
      gms_url: 'demo://catalogue',
      authenticated: false,
      version: null,
      latency_ms: null,
      error: 'Demo Mode — not connected to a DataHub instance.',
      cache: null,
    },
    cache: null,
    entities: [
      { label: 'Datasets', count: total, detail: 'Assets in the demo catalogue' },
      {
        label: 'Owners',
        count: enterpriseOwners.length,
        detail: 'Distinct owners in the demo catalogue',
      },
      {
        label: 'Domains',
        count: enterpriseDomains.length,
        detail: 'Business domains in the demo catalogue',
      },
      {
        label: 'Platforms',
        count: platformCounts.size,
        detail: 'Source systems in the demo catalogue',
      },
    ],
    coverage: [
      coverage('Ownership', owned, total, 'Assets with at least one owner'),
      coverage('Documentation', documented, total, 'Assets with a description'),
      coverage('Tags', tagged, total, 'Assets carrying at least one tag'),
      coverage('Domain assignment', domained, total, 'Assets assigned to a domain'),
    ],
    platforms: [...platformCounts.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count),
    sampleSize: total,
    totalAssets: total,
  }
}

/**
 * The GraphQL documents the integration issues.
 *
 * Static, because it describes the code rather than runtime state. Kept in
 * step with `backend/app/integrations/datahub/queries.py`.
 */
export interface GraphQLDocument {
  name: string
  purpose: string
  entity: string
}

export const GRAPHQL_DOCUMENTS: GraphQLDocument[] = [
  { name: 'listDatasets', purpose: 'Paginated catalogue browse', entity: 'Dataset' },
  { name: 'getDataset', purpose: 'One dataset with full aspects', entity: 'Dataset' },
  { name: 'getDatasetSchema', purpose: 'Column names and types', entity: 'Dataset' },
  { name: 'getDatasetOwners', purpose: 'Ownership for one asset', entity: 'Dataset' },
  { name: 'getDatasetProfiles', purpose: 'Profiling statistics', entity: 'Dataset' },
  { name: 'getDatasetUsage', purpose: 'Query and usage activity', entity: 'Dataset' },
  { name: 'getLineage', purpose: 'Upstream and downstream graph', entity: 'Lineage' },
  { name: 'searchEntities', purpose: 'Cross-entity search', entity: 'Any' },
  { name: 'listDomains', purpose: 'Business domains', entity: 'Domain' },
  { name: 'getDomain', purpose: 'One domain with its assets', entity: 'Domain' },
  { name: 'listTags', purpose: 'Classification tags', entity: 'Tag' },
  { name: 'aggregateOwners', purpose: 'Catalogue-wide owner rollup', entity: 'CorpUser · CorpGroup' },
]

/**
 * Last sync time.
 *
 * Deliberately demo-only and labelled as such: DataGuardian reads DataHub on
 * demand and does not run its own ingestion, so there is no sync timestamp to
 * report. Presenting one would imply a scheduled pipeline that does not exist.
 */
export function fetchLastSync(): Sourced<null> {
  return demoOnly(
    null,
    'DataGuardian reads DataHub on demand and runs no ingestion of its own, so there is no sync timestamp.',
  )
}
