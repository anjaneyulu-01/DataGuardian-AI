/**
 * Demo data for every surface not yet wired to the backend.
 *
 * ONE FILE ON PURPOSE: when the DataHub-backed endpoints replace these, each
 * export below maps to a specific API call (noted per export). Components
 * import from here — never define data inline — so the swap touches only this
 * file and the hooks that fetch.
 *
 * The catalogue is modelled on a plausible mid-size fintech: Snowflake +
 * Postgres + Kafka + dbt + Looker, with the failure modes DataGuardian
 * exists to catch.
 */

import type {
  ActivityEvent,
  AIAnswer,
  DocTemplate,
  Finding,
  GovernanceAsset,
  HealthSummary,
  LineageGraphEdge,
  LineageGraphNode,
  RiskTrendPoint,
  SuggestedAction,
} from '@/types/domain'

/* ---------------------------------------------------------------------------
 * Overview — replace with GET /api/v1/datasets + rule-engine aggregates.
 * ------------------------------------------------------------------------- */

export const healthSummary: HealthSummary = {
  score: 86,
  totalAssets: 412,
  healthyAssets: 341,
  criticalIssues: 7,
  coverage: 78,
  owners: 24,
  deltas: { score: 4, healthyAssets: 12, criticalIssues: -3, coverage: 6, owners: 2 },
}

/* ---------------------------------------------------------------------------
 * Governance table — replace with GET /api/v1/datasets (Page<DatasetSummary>).
 * ------------------------------------------------------------------------- */

export const governanceAssets: GovernanceAsset[] = [
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.fct_payments,PROD)',
    name: 'fct_payments',
    platform: 'Snowflake',
    domain: 'Finance',
    owner: null,
    severity: 'critical',
    coverage: 34,
    documentation: 12,
    health: 31,
    downstreamCount: 17,
    tags: ['tier-1'],
    lastModified: '2026-07-29T18:20:00Z',
    description: null,
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,customers.dim_customer,PROD)',
    name: 'dim_customer',
    platform: 'Snowflake',
    domain: 'Customer',
    owner: 'priya.nair',
    severity: 'critical',
    coverage: 61,
    documentation: 48,
    health: 44,
    downstreamCount: 23,
    tags: ['tier-1'],
    lastModified: '2026-07-31T09:12:00Z',
    description: 'Master customer dimension joined by nearly every mart.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:postgres,app.users_raw,PROD)',
    name: 'users_raw',
    platform: 'Postgres',
    domain: 'Customer',
    owner: 'app-platform',
    severity: 'high',
    coverage: 55,
    documentation: 40,
    health: 52,
    downstreamCount: 9,
    tags: [],
    lastModified: '2026-08-01T02:45:00Z',
    description: 'Raw application users table replicated from the OLTP primary.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,marketing.fct_campaign_touch,PROD)',
    name: 'fct_campaign_touch',
    platform: 'Snowflake',
    domain: 'Marketing',
    owner: 'growth-data',
    severity: 'high',
    coverage: 58,
    documentation: 35,
    health: 55,
    downstreamCount: 6,
    tags: ['pii?'],
    lastModified: '2026-07-30T15:40:00Z',
    description: 'Campaign touchpoints with hashed emails — PII tag pending review.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:kafka,events.checkout_stream,PROD)',
    name: 'checkout_stream',
    platform: 'Kafka',
    domain: 'Payments',
    owner: 'payments-core',
    severity: 'medium',
    coverage: 72,
    documentation: 61,
    health: 68,
    downstreamCount: 11,
    tags: ['streaming', 'tier-1'],
    lastModified: '2026-08-01T07:03:00Z',
    description: 'Checkout events, 7-day retention, feeds fraud scoring.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.stg_invoices,PROD)',
    name: 'stg_invoices',
    platform: 'dbt',
    domain: 'Finance',
    owner: 'analytics-eng',
    severity: 'medium',
    coverage: 80,
    documentation: 66,
    health: 71,
    downstreamCount: 4,
    tags: [],
    lastModified: '2026-07-28T11:55:00Z',
    description: 'Staging model normalising invoice line items.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,ops.dim_warehouse,PROD)',
    name: 'dim_warehouse',
    platform: 'Snowflake',
    domain: 'Operations',
    owner: 'ops-analytics',
    severity: 'low',
    coverage: 93,
    documentation: 88,
    health: 91,
    downstreamCount: 3,
    tags: ['documented'],
    lastModified: '2026-07-25T10:30:00Z',
    description: 'Warehouse locations and capacity, refreshed weekly.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.fct_revenue_daily,PROD)',
    name: 'fct_revenue_daily',
    platform: 'Snowflake',
    domain: 'Finance',
    owner: 'finance-data',
    severity: 'low',
    coverage: 96,
    documentation: 92,
    health: 94,
    downstreamCount: 14,
    tags: ['tier-1', 'documented', 'certified'],
    lastModified: '2026-08-01T05:00:00Z',
    description: 'Certified daily revenue rollup powering the exec dashboard.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:looker,dashboards.exec_kpis,PROD)',
    name: 'exec_kpis',
    platform: 'Looker',
    domain: 'Finance',
    owner: 'bi-team',
    severity: 'low',
    coverage: 90,
    documentation: 84,
    health: 89,
    downstreamCount: 0,
    tags: ['dashboard'],
    lastModified: '2026-07-31T16:10:00Z',
    description: 'Executive KPI dashboard consumed by leadership weekly.',
  },
  {
    urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,legacy.fct_orders_v1,PROD)',
    name: 'fct_orders_v1',
    platform: 'Snowflake',
    domain: 'Payments',
    owner: null,
    severity: 'high',
    coverage: 41,
    documentation: 20,
    health: 38,
    downstreamCount: 5,
    tags: ['deprecated'],
    lastModified: '2026-02-14T08:00:00Z',
    description: 'Deprecated order fact — v2 replaced it, but 5 assets still read it.',
  },
]

/* ---------------------------------------------------------------------------
 * Findings — replace with the rule-engine findings endpoint (Phase 3).
 * ------------------------------------------------------------------------- */

export const findings: Finding[] = [
  {
    id: 'f-001',
    assetName: 'fct_payments',
    assetUrn: governanceAssets[0].urn,
    severity: 'critical',
    kind: 'missing_owner',
    title: 'Tier-1 finance dataset has no owner',
    summary:
      'fct_payments feeds 17 downstream assets including the exec revenue dashboard, but no owner is assigned and documentation coverage is 12%.',
    downstreamCount: 17,
    detectedAt: '2026-08-01T06:12:00Z',
    recommendations: ['Assign Data Team', 'Generate Documentation'],
  },
  {
    id: 'f-002',
    assetName: 'dim_customer',
    assetUrn: governanceAssets[1].urn,
    severity: 'critical',
    kind: 'untagged_pii',
    title: 'Probable PII columns without PII tags',
    summary:
      'Columns email, phone_number, and date_of_birth match PII patterns but carry no PII classification. 23 downstream assets inherit the exposure.',
    downstreamCount: 23,
    detectedAt: '2026-08-01T06:12:00Z',
    recommendations: ['Apply PII tags', 'Notify data steward'],
  },
  {
    id: 'f-003',
    assetName: 'fct_orders_v1',
    assetUrn: governanceAssets[9].urn,
    severity: 'high',
    kind: 'deprecated_in_use',
    title: 'Deprecated dataset still consumed by 5 assets',
    summary:
      'fct_orders_v1 was deprecated in February but five marts still read from it, risking silently stale order numbers.',
    downstreamCount: 5,
    detectedAt: '2026-07-31T22:40:00Z',
    recommendations: ['Migrate consumers to v2', 'Set decommission date'],
  },
  {
    id: 'f-004',
    assetName: 'fct_campaign_touch',
    assetUrn: governanceAssets[3].urn,
    severity: 'high',
    kind: 'missing_documentation',
    title: 'Marketing fact undocumented ahead of audit',
    summary:
      'Documentation coverage is 35% and the hashed-email column lacks lineage to its consent source — flagged before the Q3 privacy audit.',
    downstreamCount: 6,
    detectedAt: '2026-07-31T18:05:00Z',
    recommendations: ['Generate Documentation', 'Link consent lineage'],
  },
  {
    id: 'f-005',
    assetName: 'users_raw',
    assetUrn: governanceAssets[2].urn,
    severity: 'medium',
    kind: 'schema_drift',
    title: 'Schema drift: 2 columns added upstream',
    summary:
      'Columns marketing_opt_in and locale appeared in the OLTP source but are absent from downstream staging models.',
    downstreamCount: 9,
    detectedAt: '2026-07-30T04:22:00Z',
    recommendations: ['Refresh staging model', 'Review column docs'],
  },
]

/* ---------------------------------------------------------------------------
 * Activity feed — replace with the agent run-history endpoint (Phase 3).
 * ------------------------------------------------------------------------- */

export const activityFeed: ActivityEvent[] = [
  {
    id: 'a-001',
    timestamp: '2026-08-01T06:12:00Z',
    kind: 'scan',
    title: 'Scheduled governance scan completed',
    detail: '412 assets scanned in 3m 41s — 2 new findings, 1 resolved.',
  },
  {
    id: 'a-002',
    timestamp: '2026-08-01T06:12:30Z',
    kind: 'finding',
    severity: 'critical',
    title: 'New critical finding on fct_payments',
    detail: 'No owner assigned; 17 downstream assets affected.',
  },
  {
    id: 'a-003',
    timestamp: '2026-07-31T22:40:00Z',
    kind: 'finding',
    severity: 'high',
    title: 'Deprecated dataset still in use',
    detail: 'fct_orders_v1 read by 5 consumers after deprecation.',
  },
  {
    id: 'a-004',
    timestamp: '2026-07-31T17:02:00Z',
    kind: 'docs',
    title: 'Documentation generated for stg_invoices',
    detail: 'AI drafted 14 column descriptions; approved by analytics-eng.',
  },
  {
    id: 'a-005',
    timestamp: '2026-07-31T09:15:00Z',
    kind: 'fix',
    title: 'Owner assigned to checkout_stream',
    detail: 'payments-core accepted ownership from the recommendation.',
  },
  {
    id: 'a-006',
    timestamp: '2026-07-30T06:12:00Z',
    kind: 'scan',
    title: 'Scheduled governance scan completed',
    detail: '409 assets scanned — no new critical findings.',
  },
]

/* ---------------------------------------------------------------------------
 * Risk trend — replace with findings history aggregation (Phase 3).
 * ------------------------------------------------------------------------- */

export const riskTrend: RiskTrendPoint[] = [
  { date: 'Jul 19', critical: 12, high: 21, medium: 34, low: 61 },
  { date: 'Jul 21', critical: 11, high: 22, medium: 33, low: 63 },
  { date: 'Jul 23', critical: 11, high: 19, medium: 35, low: 62 },
  { date: 'Jul 25', critical: 10, high: 18, medium: 31, low: 66 },
  { date: 'Jul 27', critical: 9, high: 18, medium: 30, low: 68 },
  { date: 'Jul 29', critical: 10, high: 16, medium: 28, low: 70 },
  { date: 'Jul 31', critical: 8, high: 15, medium: 27, low: 72 },
  { date: 'Aug 1', critical: 7, high: 14, medium: 27, low: 74 },
]

/* ---------------------------------------------------------------------------
 * AI Investigator — replace with the LangGraph agent endpoint (Phase 4).
 * The canned answers double as the demo script.
 * ------------------------------------------------------------------------- */

export const suggestedActions: SuggestedAction[] = [
  {
    id: 'missing-owners',
    title: 'Find Missing Owners',
    description: 'Surface every asset with no accountable owner, ranked by blast radius.',
    icon: 'user-x',
    prompt: 'Find datasets without owners',
  },
  {
    id: 'analyze-metadata',
    title: 'Analyze Metadata',
    description: 'Full catalogue sweep: coverage, documentation, freshness.',
    icon: 'scan-search',
    prompt: 'Analyze metadata health across the catalogue',
  },
  {
    id: 'find-pii',
    title: 'Find PII',
    description: 'Detect probable personal data missing classification tags.',
    icon: 'shield-alert',
    prompt: 'Find untagged PII across all datasets',
  },
  {
    id: 'broken-lineage',
    title: 'Broken Lineage',
    description: 'Assets whose upstream sources disappeared or drifted.',
    icon: 'unlink',
    prompt: 'Show assets with broken lineage',
  },
  {
    id: 'stale-assets',
    title: 'Stale Assets',
    description: 'Datasets not refreshed within their expected cadence.',
    icon: 'clock-alert',
    prompt: 'Which assets are stale?',
  },
  {
    id: 'duplicates',
    title: 'Duplicate Assets',
    description: 'Near-identical tables wasting storage and splitting truth.',
    icon: 'copy',
    prompt: 'Find duplicate datasets',
  },
]

export const exampleQuestions = [
  'Find datasets without owners',
  'Which assets are highest risk?',
  'Explain downstream impact of fct_payments',
  'Generate documentation for dim_customer',
]

export const aiAnswers: AIAnswer[] = [
  {
    id: 'missing-owners',
    question: 'Find datasets without owners',
    reasoning: [
      'Queried the catalogue for assets whose ownership aspect is empty.',
      'Ranked the 12 unowned assets by downstream consumer count.',
      'Cross-referenced tier tags to weight business criticality.',
    ],
    risk: {
      level: 'critical',
      statement:
        '2 of the 12 unowned assets are tier-1. fct_payments alone feeds 17 downstream assets, including the executive revenue dashboard — an unowned failure there has no accountable responder.',
    },
    evidence: [
      { label: 'fct_payments', value: '17 downstream · tier-1 · docs 12%', severity: 'critical' },
      { label: 'fct_orders_v1', value: '5 downstream · deprecated', severity: 'high' },
      { label: 'stg_sessions', value: '3 downstream', severity: 'medium' },
      { label: '9 further assets', value: '≤2 downstream each', severity: 'low' },
    ],
    recommendation:
      'Assign finance-data as owner of fct_payments today — its lineage and query history identify them as the de-facto maintainers. Batch the remaining 11 into next week’s stewardship review.',
    actions: ['Assign Data Team', 'Generate ownership report', 'Open in Governance'],
  },
  {
    id: 'highest-risk',
    question: 'Which assets are highest risk?',
    reasoning: [
      'Scored every asset on ownership, documentation, PII exposure, freshness, and blast radius.',
      'Weighted blast radius by consumer criticality, not just count.',
      'Selected assets whose composite score falls in the critical band.',
    ],
    risk: {
      level: 'critical',
      statement:
        'Risk is concentrated: 3 assets account for 61% of total catalogue risk. All three sit upstream of the executive dashboard.',
    },
    evidence: [
      { label: 'fct_payments', value: 'health 31 · no owner · 17 downstream', severity: 'critical' },
      { label: 'dim_customer', value: 'health 44 · untagged PII · 23 downstream', severity: 'critical' },
      { label: 'fct_orders_v1', value: 'health 38 · deprecated in use', severity: 'high' },
    ],
    recommendation:
      'Fix ownership and PII tagging on the top two first — both are one-action remediations that remove the majority of critical exposure.',
    actions: ['Show Downstream Impact', 'Create Governance Report'],
  },
  {
    id: 'downstream-impact',
    question: 'Explain downstream impact of fct_payments',
    reasoning: [
      'Traversed downstream lineage from fct_payments to depth 3.',
      'Classified consumers: 11 marts, 4 ML feature sets, 2 dashboards.',
      'Checked which consumers are certified or exec-facing.',
    ],
    risk: {
      level: 'high',
      statement:
        'A bad load in fct_payments reaches the certified fct_revenue_daily within one hop and the executive KPI dashboard within two. Fraud-scoring features consume it directly.',
    },
    evidence: [
      { label: 'Direct consumers', value: '17 assets (1 hop)', severity: 'high' },
      { label: 'Certified assets reached', value: 'fct_revenue_daily → exec_kpis', severity: 'critical' },
      { label: 'ML features', value: '4 fraud-scoring feature sets', severity: 'high' },
    ],
    recommendation:
      'Treat fct_payments as tier-1 with on-call ownership and add a freshness SLA — its blast radius already behaves like production infrastructure.',
    actions: ['Open Lineage Explorer', 'Assign Data Team'],
  },
  {
    id: 'generate-docs',
    question: 'Generate documentation for dim_customer',
    reasoning: [
      'Read the schema: 31 columns, 9 currently documented.',
      'Inferred column semantics from names, types, and profiling stats.',
      'Drafted descriptions in the catalogue’s house style for steward review.',
    ],
    risk: {
      level: 'medium',
      statement:
        'Documentation gaps on a 23-consumer dimension slow every downstream team; three columns match PII patterns and must be reviewed before publishing.',
    },
    evidence: [
      { label: 'Columns drafted', value: '22 of 22 missing descriptions' },
      { label: 'Needs human review', value: 'email, phone_number, date_of_birth', severity: 'high' },
      { label: 'Style source', value: 'Matched fct_revenue_daily (certified)' },
    ],
    recommendation:
      'Approve the 19 low-risk drafts as a batch, then review the three PII-adjacent columns with the data steward before they are written back to DataHub.',
    actions: ['Preview documentation', 'Send for review'],
  },
]

/** Fallback answer for free-form prompts the demo has no canned response for. */
export const fallbackAnswer: AIAnswer = {
  id: 'fallback',
  question: '',
  reasoning: [
    'Parsed the request and mapped it to catalogue signals.',
    'This capability ships with the live agent — the demo covers the four example prompts.',
  ],
  risk: {
    level: 'low',
    statement: 'No live agent is connected yet; responses beyond the demo prompts are illustrative.',
  },
  evidence: [
    { label: 'Agent status', value: 'LangGraph workflow lands in Phase 4' },
    { label: 'Data layer', value: 'DataHub integration live and tested' },
  ],
  recommendation: 'Try one of the example prompts to see a full investigation.',
  actions: ['Find datasets without owners', 'Which assets are highest risk?'],
}

/* ---------------------------------------------------------------------------
 * Lineage Explorer — replace with GET /api/v1/lineage/impact.
 * Laid out left→right: sources → warehouse → marts → consumers.
 * ------------------------------------------------------------------------- */

export const lineageNodes: LineageGraphNode[] = [
  {
    id: 'n-app-db',
    position: { x: 0, y: 120 },
    data: {
      urn: 'urn:li:dataset:(urn:li:dataPlatform:postgres,app.orders,PROD)',
      name: 'app.orders',
      platform: 'Postgres',
      kind: 'dataset',
      owner: 'app-platform',
      severity: 'low',
      tags: ['oltp'],
      description: 'Order rows from the production application database.',
      aiSummary:
        'Healthy OLTP source. Replication lag under 2 minutes for the last 30 days.',
    },
  },
  {
    id: 'n-checkout',
    position: { x: 0, y: 280 },
    data: {
      urn: 'urn:li:dataset:(urn:li:dataPlatform:kafka,events.checkout_stream,PROD)',
      name: 'checkout_stream',
      platform: 'Kafka',
      kind: 'pipeline',
      owner: 'payments-core',
      severity: 'medium',
      tags: ['streaming', 'tier-1'],
      description: 'Checkout events, 7-day retention.',
      aiSummary:
        'Schema registry drift detected twice this quarter; consumers pin to v3.',
    },
  },
  {
    id: 'n-payments',
    position: { x: 290, y: 200 },
    data: {
      urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.fct_payments,PROD)',
      name: 'fct_payments',
      platform: 'Snowflake',
      kind: 'dataset',
      owner: null,
      severity: 'critical',
      tags: ['tier-1'],
      description: null,
      aiSummary:
        'Highest-risk node in this graph: no owner, 12% documentation, and every path to the exec dashboard flows through it.',
    },
  },
  {
    id: 'n-customer',
    position: { x: 290, y: 40 },
    data: {
      urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,customers.dim_customer,PROD)',
      name: 'dim_customer',
      platform: 'Snowflake',
      kind: 'dataset',
      owner: 'priya.nair',
      severity: 'critical',
      tags: ['tier-1', 'pii?'],
      description: 'Master customer dimension.',
      aiSummary:
        'Three columns match PII patterns without classification tags; exposure inherited by 23 consumers.',
    },
  },
  {
    id: 'n-revenue',
    position: { x: 580, y: 120 },
    data: {
      urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.fct_revenue_daily,PROD)',
      name: 'fct_revenue_daily',
      platform: 'Snowflake',
      kind: 'dataset',
      owner: 'finance-data',
      severity: 'low',
      tags: ['certified'],
      description: 'Certified daily revenue rollup.',
      aiSummary:
        'Well-governed, but inherits risk from unowned fct_payments one hop upstream.',
    },
  },
  {
    id: 'n-fraud',
    position: { x: 580, y: 300 },
    data: {
      urn: 'urn:li:dataset:(urn:li:dataPlatform:snowflake,ml.fraud_features,PROD)',
      name: 'fraud_features',
      platform: 'Snowflake',
      kind: 'model',
      owner: 'ml-platform',
      severity: 'high',
      tags: ['ml'],
      description: 'Feature set for real-time fraud scoring.',
      aiSummary:
        'Consumes fct_payments directly; a bad load degrades fraud detection in production.',
    },
  },
  {
    id: 'n-exec',
    position: { x: 870, y: 120 },
    data: {
      urn: 'urn:li:dataset:(urn:li:dataPlatform:looker,dashboards.exec_kpis,PROD)',
      name: 'exec_kpis',
      platform: 'Looker',
      kind: 'dashboard',
      owner: 'bi-team',
      severity: 'low',
      tags: ['dashboard'],
      description: 'Executive KPI dashboard.',
      aiSummary:
        'Leadership-facing. Two hops from the unowned fct_payments — the blast radius that makes f-001 critical.',
    },
  },
]

export const lineageEdges: LineageGraphEdge[] = [
  { id: 'e1', source: 'n-app-db', target: 'n-payments' },
  { id: 'e2', source: 'n-checkout', target: 'n-payments' },
  { id: 'e3', source: 'n-app-db', target: 'n-customer' },
  { id: 'e4', source: 'n-payments', target: 'n-revenue' },
  { id: 'e5', source: 'n-payments', target: 'n-fraud' },
  { id: 'e6', source: 'n-customer', target: 'n-revenue' },
  { id: 'e7', source: 'n-revenue', target: 'n-exec' },
]

/* ---------------------------------------------------------------------------
 * Documentation generators — replace with Gemini-backed endpoints (Phase 4).
 * ------------------------------------------------------------------------- */

export const docTemplates: DocTemplate[] = [
  {
    id: 'readme',
    title: 'Generate README',
    description: 'A dataset README: purpose, grain, refresh cadence, caveats.',
    icon: 'book-open',
    preview: `# fct_payments

**Purpose** — One row per settled payment, the canonical source for revenue
reporting and fraud features.

**Grain** — payment_id (unique, never reused)

**Refresh** — Hourly at :15 via dbt job \`finance_hourly\`

**Caveats**
- Refunds appear as negative amounts, not separate rows.
- Amounts are minor units (cents); divide by 100 for display.
- Rows before 2024-03 lack processor_fee (backfill pending).`,
  },
  {
    id: 'dictionary',
    title: 'Generate Data Dictionary',
    description: 'Column-by-column descriptions inferred from names, types, and profiles.',
    icon: 'table-properties',
    preview: `| Column | Type | Description |
| --- | --- | --- |
| payment_id | BIGINT | Unique settled payment identifier. Primary key. |
| customer_id | BIGINT | FK → dim_customer. Never null. |
| amount_minor | BIGINT | Amount in minor units (cents). Negative = refund. |
| currency | CHAR(3) | ISO-4217 code. 96% USD in profiling window. |
| processor | VARCHAR | Payment processor slug (stripe, adyen). |
| settled_at | TIMESTAMP | Settlement time, UTC. Partition key. |`,
  },
  {
    id: 'business',
    title: 'Generate Business Description',
    description: 'A plain-language summary a non-engineer can act on.',
    icon: 'briefcase',
    preview: `**What this data is** — Every completed customer payment, updated hourly.

**Who relies on it** — Finance (revenue reporting), the fraud team (real-time
scoring), and the executive dashboard.

**Why it matters right now** — This table has no assigned owner. If numbers
look wrong on Monday's exec review, there is currently no accountable person
to triage it.`,
  },
  {
    id: 'sql',
    title: 'Generate SQL Explanation',
    description: 'Explain what a transformation query actually does, in English.',
    icon: 'code',
    preview: `**This query** builds daily revenue by:

1. Filtering \`fct_payments\` to settled, non-refund rows.
2. Converting minor units to dollars (\`amount_minor / 100\`).
3. Grouping by settlement date and currency.
4. Left-joining FX rates to normalise everything to USD — **note:** missing FX
   rows silently drop that day's non-USD revenue. Consider an inner-join guard.`,
  },
]

/* ---------------------------------------------------------------------------
 * Top risk assets (Risk Center) — derived view over governanceAssets.
 * ------------------------------------------------------------------------- */

export const topRiskAssets = [...governanceAssets]
  .sort((a, b) => a.health - b.health)
  .slice(0, 5)

export const severityCounts = {
  critical: 7,
  high: 14,
  medium: 27,
  low: 74,
} as const
