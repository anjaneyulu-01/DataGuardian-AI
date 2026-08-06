export { apiClient, toErrorMessage } from './apiClient'
export { demoOnly, live, withFallback, type DataSource, type Sourced } from './fallback'

export { analyzeQuestion, toAIAnswer, type Investigation } from './agentService'
export {
  fetchDataHubReport,
  fetchLastSync,
  GRAPHQL_DOCUMENTS,
  type CoverageMetric,
  type DataHubReport,
  type EntityBreakdown,
  type GraphQLDocument,
} from './datahubService'
export {
  downloadDocument,
  fetchDocTemplates,
  generateDocument,
  type DocKind,
  type DocRequest,
  type GeneratedDoc,
} from './documentationService'
export {
  fetchDataset,
  fetchGovernanceAssets,
  toGovernanceAsset,
  type DatasetQuery,
  type GovernancePage,
} from './governanceService'
export { fetchLineage, type LineageGraph } from './lineageService'
export {
  fetchActivity,
  fetchOverview,
  fetchRiskTrend,
  type OverviewMetrics,
} from './overviewService'
export {
  fetchRiskOverview,
  fetchRiskTrendSeries,
  fetchViolations,
  type RiskOverview,
  type SeverityCounts,
} from './riskService'
export {
  fetchApiHealth,
  fetchDataHubStatus,
  fetchLLMStatus,
  type DataHubStatus,
} from './systemService'
