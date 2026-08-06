/**
 * Demo Mode catalogue — a realistic enterprise data estate.
 *
 * Used when Demo Mode is on, or when the backend is unreachable. Six business
 * domains (Finance, HR, Sales, Marketing, Customer, Payments) with the
 * governance failures this product exists to detect.
 *
 * TWO RULES, both deliberate:
 *
 * 1. **Deterministic.** Every value is hand-written. Nothing is randomised, so
 *    a demo shows the same numbers on every run and a judge re-running a query
 *    sees a consistent story rather than a different one each time.
 * 2. **Realistic, not flattering.** The distribution mirrors a real mid-size
 *    company: a majority of assets are broadly fine, a minority are neglected,
 *    and the worst problems cluster in the domains that matter most (Finance,
 *    Payments, Customer). A catalogue where everything is broken is as
 *    unconvincing as one where nothing is.
 */

import type {
  ActivityEvent,
  Finding,
  GovernanceAsset,
  RiskTrendPoint,
  Severity,
} from '@/types/domain'

export type BusinessDomain =
  | 'Finance'
  | 'HR'
  | 'Sales'
  | 'Marketing'
  | 'Customer'
  | 'Payments'

interface AssetSeed {
  name: string
  platform: string
  domain: BusinessDomain
  owner: string | null
  description: string | null
  tags: string[]
  downstreamCount: number
  /** Days since last modification, used to derive a stable timestamp. */
  daysStale: number
}

/**
 * The catalogue seed. Health/coverage/documentation are DERIVED from these
 * facts below rather than written by hand, so the demo numbers are internally
 * consistent — an asset cannot be "undocumented" yet score 90% documentation.
 */
const SEEDS: AssetSeed[] = [
  // --- Finance: the highest-stakes domain, and the worst offender ----------
  {
    name: 'fct_payments',
    platform: 'Snowflake',
    domain: 'Finance',
    owner: null,
    description: null,
    tags: ['tier-1'],
    downstreamCount: 17,
    daysStale: 3,
  },
  {
    name: 'fct_revenue_daily',
    platform: 'Snowflake',
    domain: 'Finance',
    owner: 'finance-data',
    description: 'Certified daily revenue rollup powering the executive dashboard.',
    tags: ['tier-1', 'certified', 'documented'],
    downstreamCount: 14,
    daysStale: 0,
  },
  {
    name: 'stg_invoices',
    platform: 'dbt',
    domain: 'Finance',
    owner: 'analytics-eng',
    description: 'Staging model normalising invoice line items.',
    tags: ['documented'],
    downstreamCount: 4,
    daysStale: 6,
  },
  {
    name: 'dim_cost_centre',
    platform: 'Snowflake',
    domain: 'Finance',
    owner: 'finance-data',
    description: 'Cost centre hierarchy, refreshed nightly from the ERP.',
    tags: ['documented'],
    downstreamCount: 8,
    daysStale: 1,
  },
  {
    name: 'fct_ledger_entries',
    platform: 'Snowflake',
    domain: 'Finance',
    owner: null,
    description: 'General ledger entries.',
    tags: ['tier-1'],
    downstreamCount: 9,
    daysStale: 12,
  },

  // --- Payments: PII and a deprecated table still in use -------------------
  {
    name: 'checkout_stream',
    platform: 'Kafka',
    domain: 'Payments',
    owner: null,
    description: 'Checkout events, 7-day retention.',
    tags: ['streaming', 'tier-1'],
    downstreamCount: 11,
    daysStale: 0,
  },
  {
    name: 'fct_orders_v1',
    platform: 'Snowflake',
    domain: 'Payments',
    owner: null,
    description: 'Superseded by fct_orders_v2. Do not build on this.',
    tags: ['deprecated'],
    downstreamCount: 5,
    daysStale: 171,
  },
  {
    name: 'fct_orders_v2',
    platform: 'Snowflake',
    domain: 'Payments',
    owner: 'payments-core',
    description: 'Order facts, one row per order. Replaces v1.',
    tags: ['tier-1', 'certified', 'documented'],
    downstreamCount: 16,
    daysStale: 0,
  },
  {
    name: 'dim_payment_method',
    platform: 'Snowflake',
    domain: 'Payments',
    owner: 'payments-core',
    description: 'Payment method reference data.',
    tags: ['documented'],
    downstreamCount: 6,
    daysStale: 9,
  },
  {
    name: 'fraud_features',
    platform: 'Snowflake',
    domain: 'Payments',
    owner: 'ml-platform',
    description: 'Feature set for real-time fraud scoring.',
    tags: ['ml', 'tier-1'],
    downstreamCount: 3,
    daysStale: 0,
  },

  // --- Customer: the PII epicentre -----------------------------------------
  {
    name: 'dim_customer',
    platform: 'Snowflake',
    domain: 'Customer',
    owner: 'priya.nair',
    description: 'Master customer dimension, one row per customer.',
    // No PII tag despite holding email, DOB, and address — the finding.
    tags: ['tier-1'],
    downstreamCount: 23,
    daysStale: 1,
  },
  {
    name: 'users_raw',
    platform: 'Postgres',
    domain: 'Customer',
    owner: 'app-platform',
    description: null,
    tags: [],
    downstreamCount: 9,
    daysStale: 0,
  },
  {
    name: 'fct_support_tickets',
    platform: 'Snowflake',
    domain: 'Customer',
    owner: 'support-ops',
    description: 'Support tickets with resolution times and CSAT scores.',
    tags: ['documented'],
    downstreamCount: 5,
    daysStale: 2,
  },
  {
    name: 'dim_customer_segment',
    platform: 'dbt',
    domain: 'Customer',
    owner: 'analytics-eng',
    description: 'Behavioural segmentation, recomputed weekly.',
    tags: ['documented'],
    downstreamCount: 7,
    daysStale: 4,
  },

  // --- HR: small, sensitive, and under-governed ----------------------------
  {
    name: 'dim_employee',
    platform: 'Snowflake',
    domain: 'HR',
    owner: 'people-ops',
    // Holds salary and national ID but is tagged only 'restricted'.
    description: 'Employee master record.',
    tags: ['restricted'],
    downstreamCount: 4,
    daysStale: 8,
  },
  {
    name: 'fct_payroll',
    platform: 'Snowflake',
    domain: 'HR',
    owner: null,
    description: null,
    tags: [],
    downstreamCount: 2,
    daysStale: 21,
  },
  {
    name: 'fct_headcount_monthly',
    platform: 'Snowflake',
    domain: 'HR',
    owner: 'people-ops',
    description: 'Monthly headcount by department and location.',
    tags: ['documented'],
    downstreamCount: 3,
    daysStale: 11,
  },

  // --- Sales ----------------------------------------------------------------
  {
    name: 'fct_opportunities',
    platform: 'Snowflake',
    domain: 'Sales',
    owner: 'revops',
    description: 'Sales opportunities synced from the CRM every 15 minutes.',
    tags: ['documented', 'tier-1'],
    downstreamCount: 12,
    daysStale: 0,
  },
  {
    name: 'dim_account',
    platform: 'Snowflake',
    domain: 'Sales',
    owner: 'revops',
    description: 'Account master, deduplicated against the CRM.',
    tags: ['documented'],
    downstreamCount: 10,
    daysStale: 2,
  },
  {
    name: 'stg_crm_contacts',
    platform: 'dbt',
    domain: 'Sales',
    owner: null,
    description: null,
    tags: [],
    downstreamCount: 6,
    daysStale: 17,
  },
  {
    name: 'fct_quota_attainment',
    platform: 'Snowflake',
    domain: 'Sales',
    owner: 'revops',
    description: 'Rep quota attainment by quarter.',
    tags: ['documented'],
    downstreamCount: 2,
    daysStale: 5,
  },

  // --- Marketing -------------------------------------------------------------
  {
    name: 'fct_campaign_touch',
    platform: 'Snowflake',
    domain: 'Marketing',
    owner: 'growth-data',
    description: 'Campaign touchpoints with hashed emails.',
    tags: [],
    downstreamCount: 6,
    daysStale: 3,
  },
  {
    name: 'dim_channel',
    platform: 'Snowflake',
    domain: 'Marketing',
    owner: 'growth-data',
    description: 'Marketing channel taxonomy.',
    tags: ['documented'],
    downstreamCount: 4,
    daysStale: 14,
  },
  {
    name: 'fct_web_sessions',
    platform: 'Snowflake',
    domain: 'Marketing',
    owner: null,
    description: null,
    tags: [],
    downstreamCount: 8,
    daysStale: 1,
  },
  {
    name: 'exec_kpis',
    platform: 'Looker',
    domain: 'Marketing',
    owner: 'bi-team',
    description: 'Executive KPI dashboard consumed by leadership weekly.',
    tags: ['dashboard', 'documented'],
    downstreamCount: 0,
    daysStale: 1,
  },
]

/** Fixed clock so timestamps and therefore "3 days ago" never drift mid-demo. */
const DEMO_NOW = new Date('2026-08-05T09:00:00Z').getTime()
const DAY_MS = 86_400_000

/**
 * Derive the governance scores from the asset's actual metadata.
 *
 * Mirrors the same weighting the live `governanceService` applies to real
 * DataHub data, so Demo Mode and Live Mode grade on the same curve — a demo
 * that scored differently would teach a judge the wrong thing.
 */
function scoreAsset(seed: AssetSeed): GovernanceAsset {
  const hasOwner = Boolean(seed.owner)
  const hasDescription = Boolean(seed.description?.trim())
  const isDeprecated = seed.tags.includes('deprecated')

  const documentation = Math.min(
    100,
    (hasDescription ? 70 : 0) + Math.min(30, seed.tags.length * 15),
  )
  const facets = [hasOwner, hasDescription, seed.tags.length > 0, true]
  const coverage = Math.round((facets.filter(Boolean).length / facets.length) * 100)
  const health = Math.max(
    0,
    Math.min(
      100,
      Math.round(coverage * 0.4 + documentation * 0.4 + (hasOwner ? 20 : 0)) -
        (isDeprecated ? 15 : 0),
    ),
  )

  return {
    urn: `urn:li:dataset:(urn:li:dataPlatform:${seed.platform.toLowerCase()},${seed.domain.toLowerCase()}.${seed.name},PROD)`,
    name: seed.name,
    platform: seed.platform,
    domain: seed.domain,
    owner: seed.owner,
    severity: severityFor(health),
    coverage,
    documentation,
    health,
    downstreamCount: seed.downstreamCount,
    tags: seed.tags,
    lastModified: new Date(DEMO_NOW - seed.daysStale * DAY_MS).toISOString(),
    description: seed.description,
  }
}

function severityFor(health: number): Severity {
  if (health < 40) return 'critical'
  if (health < 60) return 'high'
  if (health < 80) return 'medium'
  return 'low'
}

/** The full demo catalogue: 25 assets across six domains. */
export const enterpriseAssets: GovernanceAsset[] = SEEDS.map(scoreAsset)

/** Distinct owners, matching what an aggregation over the catalogue returns. */
export const enterpriseOwners: string[] = [
  ...new Set(enterpriseAssets.map((a) => a.owner).filter((o): o is string => Boolean(o))),
]

export const enterpriseDomains: BusinessDomain[] = [
  'Finance',
  'Payments',
  'Customer',
  'HR',
  'Sales',
  'Marketing',
]

/**
 * Findings that a real scan of the catalogue above would produce.
 *
 * Each one references an asset that genuinely has the stated defect, so a
 * judge who clicks through from a finding to the Governance table sees the
 * numbers agree.
 */
export const enterpriseFindings: Finding[] = [
  {
    id: 'ef-001',
    assetName: 'fct_payments',
    assetUrn: enterpriseAssets[0].urn,
    severity: 'critical',
    kind: 'missing_owner',
    title: 'Tier-1 finance table has no owner and no documentation',
    summary:
      'fct_payments feeds 17 downstream assets including the certified revenue rollup and the executive dashboard, but nobody is accountable for it and it carries no description.',
    downstreamCount: 17,
    detectedAt: new Date(DEMO_NOW - 3 * 3_600_000).toISOString(),
    recommendations: ['Assign finance-data as owner', 'Generate documentation'],
  },
  {
    id: 'ef-002',
    assetName: 'dim_customer',
    assetUrn: enterpriseAssets.find((a) => a.name === 'dim_customer')!.urn,
    severity: 'critical',
    kind: 'untagged_pii',
    title: 'Probable PII with no classification tag',
    summary:
      'Columns email, date_of_birth, and home_address match personal-data patterns but carry no PII tag. 23 downstream assets inherit the exposure.',
    downstreamCount: 23,
    detectedAt: new Date(DEMO_NOW - 3 * 3_600_000).toISOString(),
    recommendations: ['Apply PII classification', 'Notify the data steward'],
  },
  {
    id: 'ef-003',
    assetName: 'fct_payroll',
    assetUrn: enterpriseAssets.find((a) => a.name === 'fct_payroll')!.urn,
    severity: 'critical',
    kind: 'untagged_pii',
    title: 'Payroll data unowned, undocumented, and unclassified',
    summary:
      'fct_payroll contains salary and national identifier columns with no owner, no description, and no restriction tag. It has not been modified in three weeks.',
    downstreamCount: 2,
    detectedAt: new Date(DEMO_NOW - 5 * 3_600_000).toISOString(),
    recommendations: ['Assign people-ops as owner', 'Apply restricted classification'],
  },
  {
    id: 'ef-004',
    assetName: 'fct_orders_v1',
    assetUrn: enterpriseAssets.find((a) => a.name === 'fct_orders_v1')!.urn,
    severity: 'high',
    kind: 'deprecated_in_use',
    title: 'Deprecated table still read by 5 assets',
    summary:
      'fct_orders_v1 was superseded in February but five consumers still read from it, risking silently stale order numbers.',
    downstreamCount: 5,
    detectedAt: new Date(DEMO_NOW - 9 * 3_600_000).toISOString(),
    recommendations: ['Migrate consumers to v2', 'Set a decommission date'],
  },
  {
    id: 'ef-005',
    assetName: 'checkout_stream',
    assetUrn: enterpriseAssets.find((a) => a.name === 'checkout_stream')!.urn,
    severity: 'high',
    kind: 'missing_owner',
    title: 'Tier-1 event stream has no owner',
    summary:
      'checkout_stream feeds fraud scoring and 11 downstream assets, but ownership was never assigned after the platform team reorganised.',
    downstreamCount: 11,
    detectedAt: new Date(DEMO_NOW - 11 * 3_600_000).toISOString(),
    recommendations: ['Assign payments-core as owner'],
  },
  {
    id: 'ef-006',
    assetName: 'fct_web_sessions',
    assetUrn: enterpriseAssets.find((a) => a.name === 'fct_web_sessions')!.urn,
    severity: 'high',
    kind: 'missing_documentation',
    title: 'Undocumented marketing fact ahead of audit',
    summary:
      'fct_web_sessions has no owner and no description, and feeds 8 downstream assets used in attribution reporting.',
    downstreamCount: 8,
    detectedAt: new Date(DEMO_NOW - 26 * 3_600_000).toISOString(),
    recommendations: ['Assign growth-data as owner', 'Generate documentation'],
  },
  {
    id: 'ef-007',
    assetName: 'stg_crm_contacts',
    assetUrn: enterpriseAssets.find((a) => a.name === 'stg_crm_contacts')!.urn,
    severity: 'medium',
    kind: 'stale_asset',
    title: 'Staging model not refreshed in 17 days',
    summary:
      'stg_crm_contacts is expected to refresh daily but has not changed in 17 days. Six downstream assets may be serving stale contact data.',
    downstreamCount: 6,
    detectedAt: new Date(DEMO_NOW - 30 * 3_600_000).toISOString(),
    recommendations: ['Check the dbt job schedule', 'Assign revops as owner'],
  },
]

/**
 * Two weeks of risk history.
 *
 * Trends downward — a governance programme that is working. Hand-written so
 * the same shape appears every run.
 */
export const enterpriseRiskTrend: RiskTrendPoint[] = [
  { date: 'Jul 23', critical: 6, high: 9, medium: 7, low: 3 },
  { date: 'Jul 25', critical: 6, high: 8, medium: 8, low: 3 },
  { date: 'Jul 27', critical: 5, high: 8, medium: 7, low: 5 },
  { date: 'Jul 29', critical: 5, high: 7, medium: 7, low: 6 },
  { date: 'Jul 31', critical: 4, high: 7, medium: 6, low: 8 },
  { date: 'Aug 2', critical: 4, high: 6, medium: 6, low: 9 },
  { date: 'Aug 4', critical: 3, high: 5, medium: 6, low: 11 },
  { date: 'Aug 5', critical: 3, high: 4, medium: 6, low: 12 },
]

export const enterpriseActivity: ActivityEvent[] = [
  {
    id: 'ea-001',
    timestamp: new Date(DEMO_NOW - 2 * 3_600_000).toISOString(),
    kind: 'scan',
    title: 'Scheduled governance scan completed',
    detail: '25 assets scanned in 4.2s — 7 findings, 2 resolved since the last run.',
  },
  {
    id: 'ea-002',
    timestamp: new Date(DEMO_NOW - 3 * 3_600_000).toISOString(),
    kind: 'finding',
    severity: 'critical',
    title: 'New critical finding in Finance',
    detail: 'fct_payments lost its owner when the data platform team reorganised.',
  },
  {
    id: 'ea-003',
    timestamp: new Date(DEMO_NOW - 5 * 3_600_000).toISOString(),
    kind: 'finding',
    severity: 'critical',
    title: 'Unclassified PII detected in HR',
    detail: 'fct_payroll holds salary and national ID columns with no restriction tag.',
  },
  {
    id: 'ea-004',
    timestamp: new Date(DEMO_NOW - 20 * 3_600_000).toISOString(),
    kind: 'docs',
    title: 'Documentation generated for dim_cost_centre',
    detail: 'AI drafted 11 column descriptions; approved by finance-data.',
  },
  {
    id: 'ea-005',
    timestamp: new Date(DEMO_NOW - 28 * 3_600_000).toISOString(),
    kind: 'fix',
    title: 'Owner assigned to fct_opportunities',
    detail: 'revops accepted ownership from an agent recommendation.',
  },
  {
    id: 'ea-006',
    timestamp: new Date(DEMO_NOW - 50 * 3_600_000).toISOString(),
    kind: 'scan',
    title: 'Scheduled governance scan completed',
    detail: '25 assets scanned — 9 findings.',
  },
]

/** Headline metrics, computed from the catalogue so they always reconcile. */
export function enterpriseMetrics() {
  const assets = enterpriseAssets
  const missingOwners = assets.filter((a) => !a.owner).length
  const undocumented = assets.filter((a) => !a.description).length

  return {
    totalAssets: assets.length,
    healthyAssets: assets.filter((a) => a.health >= 80).length,
    criticalIssues: assets.filter((a) => a.severity === 'critical').length,
    missingOwners,
    owners: enterpriseOwners.length,
    domains: enterpriseDomains.length,
    coverage: Math.round(
      assets.reduce((sum, a) => sum + a.coverage, 0) / assets.length,
    ),
    documentationCoverage: Math.round(
      ((assets.length - undocumented) / assets.length) * 100,
    ),
    // Assets with at least one downstream consumer — how much of the estate
    // the lineage graph actually covers.
    lineageCoverage: Math.round(
      (assets.filter((a) => a.downstreamCount > 0).length / assets.length) * 100,
    ),
    score: Math.round(assets.reduce((sum, a) => sum + a.health, 0) / assets.length),
  }
}
