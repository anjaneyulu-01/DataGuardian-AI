import { useEffect, useState } from 'react'

import { fetchHealth, toErrorMessage } from '@/services'
import type { HealthStatus } from '@/types'

type BackendState =
  | { state: 'loading' }
  | { state: 'ready'; health: HealthStatus }
  | { state: 'error'; message: string }

/**
 * Polls the backend health endpoint once on mount.
 * Exists so the shell can show whether FastAPI is reachable — it is wiring
 * verification, not a governance feature.
 */
export function useBackendStatus(): BackendState {
  const [status, setStatus] = useState<BackendState>({ state: 'loading' })

  useEffect(() => {
    let active = true

    fetchHealth()
      .then((health) => {
        if (active) setStatus({ state: 'ready', health })
      })
      .catch((error: unknown) => {
        if (active) setStatus({ state: 'error', message: toErrorMessage(error) })
      })

    return () => {
      active = false
    }
  }, [])

  return status
}
