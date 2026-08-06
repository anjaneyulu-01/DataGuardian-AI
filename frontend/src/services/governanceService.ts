/**
 * Governance catalogue.
 *
 * Live source: `GET /api/v1/datasets`, which returns DataHub metadata.
 *
 * Coverage / documentation / health percentages are DERIVED here from the
 * metadata DataHub actually holds. They are presentation-layer heuristics for
 * the table's progress bars — the authoritative governance verdict is the
 * agent's risk score, which the backend computes deterministically. Both are
 * shown, and only the agent's number is ever called a "risk score".
 */

import { apiClient } from './apiClient'
import { withFallback, type Sourced } from './fallback'
import { enterpriseAssets } from '@/data/enterpriseCatalogue'
import type { ApiDatasetSummary, ApiPage } from '@/types/api'
import type { GovernanceAsset, Severity } from '@/types/domain'

export interface DatasetQuery {
  search?: string
  start?: number
  count?: number
}

export interface GovernancePage {
  assets: GovernanceAsset[]
  total: number
  start: number
}

/** Map a DataHub dataset onto the row shape the table renders. */
export function toGovernanceAsset(dataset: ApiDatasetSummary): GovernanceAsset {
  const hasOwner = dataset.owners.length > 0
  const hasDescription = Boolean(dataset.description?.trim())
  const isDeprecated = Boolean(dataset.deprecation?.deprecated)

  // Documentation: description presence dominates, tags contribute a little
  // because a tagged asset is at least partly classified.
  const documentation = (hasDescription ? 70 : 0) + Math.min(30, dataset.tags.length * 15)

  // Coverage: how many of the four metadata facets DataHub actually holds.
  const facets = [hasOwner, hasDescription, dataset.tags.length > 0, Boolean(dataset.domain)]
  const coverage = Math.round((facets.filter(Boolean).length / facets.length) * 100)

  // Health weights ownership highest — it is the prerequisite for every other
  // governance control.
  const health = Math.max(
    0,
    Math.round(coverage * 0.4 + documentation * 0.4 + (hasOwner ? 20 : 0)) -
      (isDeprecated ? 15 : 0),
  )

  return {
    urn: dataset.urn,
    name: dataset.name ?? dataset.urn.split(',').slice(-2, -1)[0] ?? 'unknown',
    platform: dataset.platform?.display_name ?? dataset.platform?.name ?? 'unknown',
    domain: dataset.domain?.name ?? 'Unassigned',
    owner:
      dataset.owners[0]?.display_name ?? dataset.owners[0]?.name ?? null,
    severity: severityFromHealth(health),
    coverage,
    documentation: Math.min(100, documentation),
    health: Math.min(100, health),
    downstreamCount: 0, // filled by the lineage service when an asset is opened
    tags: dataset.tags.map((tag) => tag.name),
    lastModified: dataset.last_modified ?? dataset.last_ingested ?? new Date().toISOString(),
    description: dataset.description,
  }
}

function severityFromHealth(health: number): Severity {
  if (health < 40) return 'critical'
  if (health < 60) return 'high'
  if (health < 80) return 'medium'
  return 'low'
}

export async function fetchGovernanceAssets(
  query: DatasetQuery = {},
): Promise<Sourced<GovernancePage>> {
  const { search = '', start = 0, count = 50 } = query

  return withFallback(
    async () => {
      const { data } = await apiClient.get<ApiPage<ApiDatasetSummary>>('/v1/datasets', {
        params: { query: search.trim() || '*', start, count },
      })
      return {
        assets: data.results.map(toGovernanceAsset),
        total: data.total,
        start: data.start,
      }
    },
    () => ({ assets: enterpriseAssets, total: enterpriseAssets.length, start: 0 }),
    'governanceService.list',
  )
}

export async function fetchDataset(urn: string): Promise<Sourced<GovernanceAsset>> {
  return withFallback(
    async () => {
      const { data } = await apiClient.get<ApiDatasetSummary>(
        `/v1/datasets/${encodeURIComponent(urn)}`,
      )
      return toGovernanceAsset(data)
    },
    () => enterpriseAssets.find((a) => a.urn === urn) ?? enterpriseAssets[0],
    'governanceService.get',
  )
}
