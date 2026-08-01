/**
 * Product domain types.
 *
 * These describe what the UI renders. They deliberately mirror the backend's
 * DataHub models (`backend/app/integrations/datahub/models.py`) where they
 * overlap, so swapping mock data for live API responses is a mapping exercise,
 * not a redesign.
 */

export type Severity = 'critical' | 'high' | 'medium' | 'low'

export type FindingKind =
  | 'missing_owner'
  | 'missing_documentation'
  | 'untagged_pii'
  | 'stale_asset'
  | 'deprecated_in_use'
  | 'schema_drift'

export interface GovernanceAsset {
  urn: string
  name: string
  platform: string
  domain: string
  owner: string | null
  severity: Severity
  /** 0–100. How complete this asset's required metadata is. */
  coverage: number
  /** 0–100. Description + column docs completeness. */
  documentation: number
  /** 0–100. Composite governance health. */
  health: number
  downstreamCount: number
  tags: string[]
  lastModified: string
  description: string | null
}

export interface Finding {
  id: string
  assetName: string
  assetUrn: string
  severity: Severity
  kind: FindingKind
  title: string
  summary: string
  downstreamCount: number
  detectedAt: string
  recommendations: string[]
}

export interface ActivityEvent {
  id: string
  timestamp: string
  kind: 'scan' | 'finding' | 'fix' | 'docs' | 'system'
  title: string
  detail: string
  severity?: Severity
}

export interface RiskTrendPoint {
  /** Short label, e.g. "Jul 26". */
  date: string
  critical: number
  high: number
  medium: number
  low: number
}

export interface HealthSummary {
  /** 0–100 governance health score. */
  score: number
  totalAssets: number
  healthyAssets: number
  criticalIssues: number
  /** 0–100 metadata coverage across the catalogue. */
  coverage: number
  /** Distinct owners across the catalogue. */
  owners: number
  /** Week-over-week deltas, positive = improved. */
  deltas: {
    score: number
    healthyAssets: number
    criticalIssues: number
    coverage: number
    owners: number
  }
}

/* --- AI Investigator ------------------------------------------------------ */

export interface EvidenceItem {
  label: string
  value: string
  severity?: Severity
}

export interface AIAnswer {
  /** Matches a suggested prompt; used to select the canned demo answer. */
  id: string
  question: string
  reasoning: string[]
  risk: { level: Severity; statement: string }
  evidence: EvidenceItem[]
  recommendation: string
  actions: string[]
}

export interface SuggestedAction {
  id: string
  title: string
  description: string
  icon: string
  prompt: string
}

/* --- Lineage -------------------------------------------------------------- */

export interface LineageNodeData {
  urn: string
  name: string
  platform: string
  kind: 'source' | 'dataset' | 'dashboard'
  owner: string | null
  severity: Severity
  tags: string[]
  description: string | null
  aiSummary: string
  [key: string]: unknown
}

export interface LineageGraphNode {
  id: string
  position: { x: number; y: number }
  data: LineageNodeData
}

export interface LineageGraphEdge {
  id: string
  source: string
  target: string
}

/* --- Documentation -------------------------------------------------------- */

export interface DocTemplate {
  id: string
  title: string
  description: string
  icon: string
  /** Markdown-ish preview shown when this generator is selected. */
  preview: string
}
