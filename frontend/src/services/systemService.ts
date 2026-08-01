import { apiClient } from './apiClient'
import type { HealthStatus } from '@/types'

/** Shape of `GET /api/v1/health/datahub` (see backend DataHubHealthReport). */
export interface DataHubStatus {
  reachable: boolean
  gms_url: string
  authenticated: boolean
  version: string | null
  latency_ms: number | null
  error: string | null
  cache?: {
    hits: number
    misses: number
    entries: number
    evictions: number
    hit_rate: number
  } | null
}

export async function fetchApiHealth(): Promise<HealthStatus> {
  const { data } = await apiClient.get<HealthStatus>('/v1/health')
  return data
}

export async function fetchDataHubStatus(): Promise<DataHubStatus> {
  const { data } = await apiClient.get<DataHubStatus>('/v1/health/datahub')
  return data
}
