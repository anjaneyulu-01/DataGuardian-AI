import axios, { AxiosError } from 'axios'

import type { ApiError } from '@/types'

/**
 * Resolve the API base URL for this build.
 *
 * Two very different hosting models, and getting this wrong is the classic
 * static-site deployment failure:
 *
 * * **Development** — the Vite dev server proxies `/api` to FastAPI (see
 *   `vite.config.ts`), so a relative path is correct and avoids CORS entirely.
 * * **Production (Render Static Site)** — there is no proxy. A relative
 *   `/api` would resolve against the static site's own domain and 404 on
 *   every call, so an absolute backend URL is required.
 *
 * `VITE_API_URL` is the documented name; `VITE_API_BASE_URL` is accepted as an
 * alias because earlier builds used it and silently ignoring a set variable
 * is worse than accepting both.
 *
 * Vite inlines these at BUILD time, so changing them on Render requires a
 * rebuild, not just a restart. The deployment guide says so explicitly.
 */
function resolveBaseUrl(): string {
  const configured =
    import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE_URL

  if (configured) {
    const trimmed = String(configured).replace(/\/+$/, '')

    // Accept a bare origin as well as one already ending in /api. Render's
    // `fromService` wiring resolves to `https://api.onrender.com` with no
    // path, and requiring a hand-edited suffix there is exactly the kind of
    // detail that produces a green build serving 404s.
    try {
      const url = new URL(trimmed)
      if (url.pathname === '' || url.pathname === '/') return `${trimmed}/api`
    } catch {
      // Not absolute (e.g. a relative override in a test). Use it verbatim.
    }
    return trimmed
  }

  if (import.meta.env.PROD) {
    // A production bundle with no backend URL cannot reach an API. Fail loudly
    // in the console rather than leaving a developer to guess why every panel
    // silently fell back to demo data.
    console.error(
      '[DataGuardian] VITE_API_URL is not set. This production build has no ' +
        'backend URL, so every request will fail and the UI will fall back to ' +
        'Demo Mode. Set it to the backend origin plus /api — for example ' +
        'https://dataguardian-api.onrender.com/api — then redeploy, because ' +
        'Vite inlines this value at build time. Note the path ends at /api: ' +
        'service calls append /v1/... themselves.',
    )
  }

  // Dev default: the Vite proxy handles it.
  return '/api'
}

export const API_BASE_URL = resolveBaseUrl()

/** Single Axios instance for every backend call. */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

/** Pulls a human-readable message out of any thrown request error. */
export function toErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as ApiError | undefined)?.detail
    if (detail) return detail

    // A cross-origin rejection and a dead server both surface as a bare
    // "Network Error", which tells a deployer nothing. Name the likely cause.
    if (error.code === 'ERR_NETWORK') {
      return (
        `Cannot reach the API at ${API_BASE_URL}. The backend may be asleep ` +
        `(Render free tier cold-starts take ~50s), down, or missing this ` +
        `origin in CORS_ORIGINS.`
      )
    }
    if (error.code === 'ECONNABORTED') {
      return `The API did not respond in time (${API_BASE_URL}).`
    }
    return error.message
  }
  return error instanceof Error ? error.message : 'Unexpected error'
}

// Normalises rejections so callers always receive an Error, never a raw
// Axios payload. Auth headers and retry policy will hook in here later.
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(new Error(toErrorMessage(error))),
)
