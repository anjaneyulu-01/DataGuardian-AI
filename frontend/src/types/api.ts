/**
 * Backend response contracts.
 *
 * These mirror the Pydantic models the API actually returns — `AgentResult`
 * in `backend/app/agents/state.py`, and the DataHub models in
 * `backend/app/integrations/datahub/models.py`. Field names are snake_case
 * because that is what the wire carries; the mapping to camelCase view models
 * happens in the service layer, not in components.
 */

/* --- System ---------------------------------------------------------------- */

export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down'
  version: string
  environment: string
  /** Whether background scanning is running. Drives the Scheduler indicator. */
  scheduler_enabled: boolean
}

export interface CacheStats {
  hits: number
  misses: number
  entries: number
  evictions: number
  hit_rate: number
}

export interface DataHubHealth {
  reachable: boolean
  gms_url: string
  authenticated: boolean
  version: string | null
  latency_ms: number | null
  error: string | null
  cache?: CacheStats | null
}

export interface LLMHealth {
  provider: string
  configured: boolean
  reachable: boolean
  model: string
  latency_ms: number | null
  error: string | null
  fallback_chain?: string[]
}

/* --- DataHub entities ------------------------------------------------------ */

export interface ApiOwner {
  urn: string
  kind: 'USER' | 'GROUP' | 'UNKNOWN'
  name: string | null
  display_name: string | null
  email: string | null
  title: string | null
  active: boolean | null
  ownership_type: string | null
  asset_count: number | null
}

export interface ApiTag {
  urn: string
  name: string
  description: string | null
  color_hex: string | null
}

export interface ApiPlatform {
  urn: string
  name: string
  display_name: string | null
}

export interface ApiDomain {
  urn: string
  id: string | null
  name: string | null
  description: string | null
  owners: ApiOwner[]
  entity_count: number | null
}

export interface ApiDeprecation {
  deprecated: boolean
  note: string | null
  decommission_time: string | null
}

export interface ApiSchemaField {
  field_path: string
  label: string | null
  description: string | null
  type: string | null
  native_data_type: string | null
  nullable: boolean | null
  is_part_of_key: boolean
}

export interface ApiDatasetSchema {
  name: string | null
  primary_keys: string[]
  fields: ApiSchemaField[]
  field_count: number
}

export interface ApiDatasetSummary {
  urn: string
  name: string | null
  qualified_name: string | null
  platform: ApiPlatform | null
  description: string | null
  sub_types: string[]
  owners: ApiOwner[]
  domain: ApiDomain | null
  tags: ApiTag[]
  deprecation: ApiDeprecation | null
  external_url: string | null
  last_modified: string | null
  last_ingested: string | null
}

export interface ApiDataset extends ApiDatasetSummary {
  glossary_terms: { urn: string; name: string; description: string | null }[]
  schema_metadata: ApiDatasetSchema | null
  custom_properties: Record<string, string>
  institutional_memory: { url: string; description: string | null }[]
  created: string | null
}

export interface ApiPage<T> {
  start: number
  count: number
  total: number
  results: T[]
  has_more: boolean
}

/* --- Lineage --------------------------------------------------------------- */

export interface ApiLineageNode {
  urn: string
  entity_type: string
  name: string | null
  qualified_name: string | null
  description: string | null
  platform: ApiPlatform | null
  degree: number | null
  deprecated: boolean
}

export interface ApiLineage {
  urn: string
  direction: 'UPSTREAM' | 'DOWNSTREAM'
  total: number
  nodes: ApiLineageNode[]
}

export interface ApiImpact {
  upstream: ApiLineage
  downstream: ApiLineage
}

/* --- Agent ----------------------------------------------------------------- */

export type ApiSeverity = 'critical' | 'high' | 'medium' | 'low'

export type ApiIntent =
  | 'find_missing_owners'
  | 'analyze_governance'
  | 'analyze_lineage'
  | 'find_risky_datasets'
  | 'generate_documentation'
  | 'generate_report'
  | 'unknown'

export interface ApiFinding {
  rule: string
  title: string
  severity: ApiSeverity
  points: number
  asset_urn: string | null
  asset_name: string | null
  detail: string
}

export interface ApiRecommendation {
  action: string
  rationale: string
  priority: ApiSeverity
  asset_urn: string | null
}

export interface ApiTraceEntry {
  node: string
  status: 'ok' | 'skipped' | 'failed'
  duration_ms: number
  detail: string
  error: string | null
}

/** Response of `POST /api/v1/agent/analyze`. */
export interface ApiAgentResult {
  question: string
  intent: ApiIntent
  summary: string
  risk_level: ApiSeverity
  risk_score: number
  findings: ApiFinding[]
  recommendations: ApiRecommendation[]
  evidence: Record<string, unknown>[]
  business_impact: string
  next_steps: string[]
  trace: ApiTraceEntry[]
  errors: string[]
  degraded: boolean
  duration_ms: number
  llm_provider: string
  tools_used: string[]
}

export interface ApiError {
  detail: string
}
