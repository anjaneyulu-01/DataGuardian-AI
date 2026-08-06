import { apiClient } from './apiClient'
import type { DataHubHealth, HealthStatus, LLMHealth } from '@/types/api'

/** Re-exported under the old name so existing imports keep working. */
export type DataHubStatus = DataHubHealth

export async function fetchApiHealth(): Promise<HealthStatus> {
  const { data } = await apiClient.get<HealthStatus>('/v1/health')
  return data
}

export async function fetchDataHubStatus(): Promise<DataHubHealth> {
  const { data } = await apiClient.get<DataHubHealth>('/v1/health/datahub')
  return data
}

export async function fetchLLMStatus(): Promise<LLMHealth> {
  const { data } = await apiClient.get<LLMHealth>('/v1/health/llm')
  return data
}
