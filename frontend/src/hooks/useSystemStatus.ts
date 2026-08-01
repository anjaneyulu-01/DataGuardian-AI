import { useEffect, useState } from 'react'

import {
  fetchApiHealth,
  fetchDataHubStatus,
  type DataHubStatus,
} from '@/services/systemService'

export type LinkState = 'checking' | 'online' | 'offline'

export interface SystemStatus {
  api: LinkState
  datahub: LinkState
  datahubVersion: string | null
}

const POLL_MS = 30_000

/**
 * Live status of the two real backends, shown in the top bar.
 *
 * This hook talks to the actual API — it is one of the two places in the UI
 * that is NOT mock data (the other is anything reading these statuses).
 * Polls every 30s; both checks are independent so a DataHub outage does not
 * mark the API offline.
 */
export function useSystemStatus(): SystemStatus {
  const [api, setApi] = useState<LinkState>('checking')
  const [datahub, setDatahub] = useState<LinkState>('checking')
  const [datahubVersion, setDatahubVersion] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    const check = async () => {
      try {
        await fetchApiHealth()
        if (active) setApi('online')
      } catch {
        if (active) setApi('offline')
      }

      try {
        const status: DataHubStatus = await fetchDataHubStatus()
        if (active) {
          setDatahub(status.reachable ? 'online' : 'offline')
          setDatahubVersion(status.version)
        }
      } catch {
        if (active) setDatahub('offline')
      }
    }

    void check()
    const interval = setInterval(() => void check(), POLL_MS)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  return { api, datahub, datahubVersion }
}
