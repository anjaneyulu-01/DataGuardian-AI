import { apiClient } from './apiClient'
import type { HealthStatus } from '@/types'

/** Reads backend liveness. Used to confirm the frontend/backend wiring. */
export async function fetchHealth(): Promise<HealthStatus> {
  const { data } = await apiClient.get<HealthStatus>('/v1/health')
  return data
}
