import axios, { AxiosError } from 'axios'

import type { ApiError } from '@/types'

/**
 * Single Axios instance for every backend call.
 *
 * Defaults to the relative `/api` path, which the Vite dev server proxies to
 * FastAPI (see `vite.config.ts`). Set `VITE_API_BASE_URL` to point at an
 * absolute backend URL in deployed environments.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

/** Pulls a human-readable message out of any thrown request error. */
export function toErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as ApiError | undefined)?.detail
    return detail ?? error.message
  }
  return error instanceof Error ? error.message : 'Unexpected error'
}

// Normalises rejections so callers always receive an Error, never a raw
// Axios payload. Auth headers and retry policy will hook in here later.
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(new Error(toErrorMessage(error))),
)
