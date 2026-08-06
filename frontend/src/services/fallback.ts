/**
 * Live-with-fallback pattern for every service.
 *
 * The backend may be down, or an endpoint may not exist yet (scan history and
 * risk trends land in a later phase). Rather than crashing or — worse —
 * silently showing demo numbers as if they were real, every service returns
 * its payload tagged with a `source`.
 *
 * The UI surfaces that tag. Showing invented governance figures as though
 * they came from a real catalogue is exactly the failure mode this product
 * exists to prevent, so "demo data" must always be visibly labelled.
 */

import { isDemoModeEnabled } from '@/app/demoMode'

import { toErrorMessage } from './apiClient'

export type DataSource = 'live' | 'demo'

export interface Sourced<T> {
  data: T
  source: DataSource
  /** Why the fallback engaged. Shown in a tooltip, never swallowed. */
  reason?: string
}

/**
 * Try the live call; fall back to demo data if it fails.
 *
 * @param live Function performing the real API call.
 * @param demo Produces the fallback payload. Lazy so the mock cost is only
 *   paid when actually needed.
 * @param label Used in the console warning to identify which call degraded.
 */
export async function withFallback<T>(
  live: () => Promise<T>,
  demo: () => T,
  label: string,
): Promise<Sourced<T>> {
  // Demo Mode short-circuits before the network call. Attempting the request
  // and discarding the result would waste a round-trip and, worse, make the
  // toggle feel slow on a healthy backend.
  if (isDemoModeEnabled()) {
    return {
      data: demo(),
      source: 'demo',
      reason: 'Demo Mode is on — showing the sample enterprise catalogue.',
    }
  }

  try {
    return { data: await live(), source: 'live' }
  } catch (error) {
    const reason = toErrorMessage(error)
    // Warn rather than throw: a degraded panel beats a blank page, but the
    // failure must still be visible to a developer.
    console.warn(`[${label}] live data unavailable, using demo data:`, reason)
    return {
      data: demo(),
      source: 'demo',
      reason: `Live data unavailable (${reason}). Live mode needs the backend and DataHub running.`,
    }
  }
}

/** Marks a payload that never had a live endpoint to begin with. */
export function demoOnly<T>(data: T, reason: string): Sourced<T> {
  return { data, source: 'demo', reason }
}

/** Marks a payload that came straight from the API. */
export function live<T>(data: T): Sourced<T> {
  return { data, source: 'live' }
}
