/**
 * React Query hooks — the only place components fetch data.
 *
 * Query keys are centralised in `queryKeys` so an invalidation cannot miss a
 * cache entry through a typo, and every hook returns the `Sourced<T>` wrapper
 * so pages can label demo data.
 *
 * Stale times are chosen per data type rather than globally: DataHub metadata
 * changes on an ingestion cadence (minutes), while health checks are cheap and
 * worth polling.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'

import {
  analyzeQuestion,
  fetchActivity,
  fetchApiHealth,
  fetchDataHubReport,
  fetchDataHubStatus,
  fetchDocTemplates,
  fetchGovernanceAssets,
  fetchLLMStatus,
  fetchLineage,
  fetchOverview,
  fetchRiskOverview,
  fetchRiskTrendSeries,
  fetchViolations,
  generateDocument,
  type DatasetQuery,
  type DocRequest,
  type GeneratedDoc,
  type Investigation,
  type Sourced,
} from '@/services'
import type { DataHubHealth, HealthStatus, LLMHealth } from '@/types/api'

/** Every cache key in the app. */
export const queryKeys = {
  health: {
    api: ['health', 'api'] as const,
    datahub: ['health', 'datahub'] as const,
    llm: ['health', 'llm'] as const,
  },
  overview: {
    metrics: ['overview', 'metrics'] as const,
    activity: ['overview', 'activity'] as const,
  },
  governance: {
    list: (query: DatasetQuery) => ['governance', 'list', query] as const,
  },
  risk: {
    overview: ['risk', 'overview'] as const,
    trend: ['risk', 'trend'] as const,
    violations: ['risk', 'violations'] as const,
  },
  lineage: {
    graph: (urn: string | null) => ['lineage', 'graph', urn] as const,
  },
  documentation: {
    templates: ['documentation', 'templates'] as const,
  },
  datahub: {
    report: ['datahub', 'report'] as const,
  },
} as const

// Metadata moves on an ingestion cadence, so a minute of staleness is free.
const METADATA_STALE_MS = 60_000
// Health is cheap and the badge should feel live.
const HEALTH_STALE_MS = 15_000
const HEALTH_POLL_MS = 30_000

/* --- Health ---------------------------------------------------------------- */

export function useApiHealth(): UseQueryResult<HealthStatus> {
  return useQuery({
    queryKey: queryKeys.health.api,
    queryFn: fetchApiHealth,
    staleTime: HEALTH_STALE_MS,
    refetchInterval: HEALTH_POLL_MS,
    // A failing health check IS the answer; retrying just delays showing it.
    retry: false,
  })
}

export function useDataHubHealth(): UseQueryResult<DataHubHealth> {
  return useQuery({
    queryKey: queryKeys.health.datahub,
    queryFn: fetchDataHubStatus,
    staleTime: HEALTH_STALE_MS,
    refetchInterval: HEALTH_POLL_MS,
    retry: false,
  })
}

export function useLLMHealth(): UseQueryResult<LLMHealth> {
  return useQuery({
    queryKey: queryKeys.health.llm,
    queryFn: fetchLLMStatus,
    staleTime: HEALTH_STALE_MS,
    // Polling this costs a round-trip to the provider, so only on demand.
    retry: false,
  })
}

/* --- Overview -------------------------------------------------------------- */

export function useOverview() {
  return useQuery({
    queryKey: queryKeys.overview.metrics,
    queryFn: fetchOverview,
    staleTime: METADATA_STALE_MS,
  })
}

export function useActivity() {
  return useQuery({
    queryKey: queryKeys.overview.activity,
    queryFn: fetchActivity,
    staleTime: METADATA_STALE_MS,
  })
}

/* --- DataHub --------------------------------------------------------------- */

/**
 * The DataHub integration report.
 *
 * Shorter stale time than other metadata: this page is the evidence that the
 * connection is live, so a stale cache entry would undercut the thing it is
 * there to show.
 */
export function useDataHubReport() {
  return useQuery({
    queryKey: queryKeys.datahub.report,
    queryFn: fetchDataHubReport,
    staleTime: HEALTH_STALE_MS,
  })
}

/* --- Governance ------------------------------------------------------------ */

export function useGovernanceAssets(query: DatasetQuery = {}) {
  return useQuery({
    queryKey: queryKeys.governance.list(query),
    queryFn: () => fetchGovernanceAssets(query),
    staleTime: METADATA_STALE_MS,
    // Keeps the previous page visible while the next loads, so the table does
    // not flash empty on every keystroke or page change.
    placeholderData: (previous) => previous,
  })
}

/* --- Risk ------------------------------------------------------------------ */

export function useRiskOverview() {
  return useQuery({
    queryKey: queryKeys.risk.overview,
    queryFn: fetchRiskOverview,
    staleTime: METADATA_STALE_MS,
  })
}

export function useRiskTrend() {
  return useQuery({
    queryKey: queryKeys.risk.trend,
    queryFn: fetchRiskTrendSeries,
    staleTime: METADATA_STALE_MS,
  })
}

export function useViolations() {
  return useQuery({
    queryKey: queryKeys.risk.violations,
    queryFn: fetchViolations,
    staleTime: METADATA_STALE_MS,
  })
}

/* --- Lineage --------------------------------------------------------------- */

export function useLineage(urn: string | null) {
  return useQuery({
    queryKey: queryKeys.lineage.graph(urn),
    queryFn: () => fetchLineage(urn),
    staleTime: METADATA_STALE_MS,
  })
}

/* --- Documentation --------------------------------------------------------- */

export function useDocTemplates() {
  return useQuery({
    queryKey: queryKeys.documentation.templates,
    queryFn: fetchDocTemplates,
    // Static definitions; no point ever refetching.
    staleTime: Infinity,
  })
}

export function useGenerateDocument(): UseMutationResult<
  Sourced<GeneratedDoc>,
  Error,
  DocRequest
> {
  return useMutation({
    mutationFn: generateDocument,
    // Generation is an LLM round-trip; a retry doubles the wait and the cost.
    retry: false,
  })
}

/* --- Agent ----------------------------------------------------------------- */

/**
 * Run an investigation.
 *
 * A mutation rather than a query: each question is an action with a cost, not
 * a cacheable read, and firing it on mount would be wrong.
 */
export function useAnalyze(): UseMutationResult<Sourced<Investigation>, Error, string> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: analyzeQuestion,
    retry: false,
    onSuccess: (result) => {
      // A live run reflects the current catalogue, so any panel derived from
      // the same metadata is now potentially stale.
      if (result.source === 'live') {
        void queryClient.invalidateQueries({ queryKey: queryKeys.overview.metrics })
        void queryClient.invalidateQueries({ queryKey: queryKeys.risk.overview })
      }
    },
  })
}
