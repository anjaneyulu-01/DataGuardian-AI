/**
 * Shared response shapes returned by the DataGuardian AI backend.
 * Domain types (assets, findings, remediation actions) get added here as the
 * corresponding backend endpoints land.
 */

/** Payload of `GET /` on the backend. */
export interface ServiceInfo {
  project: string
  status: string
}

/** Payload of `GET /api/v1/health`. */
export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down'
  version: string
  environment: string
}

/** Envelope used by the backend for any handled error. */
export interface ApiError {
  detail: string
}
