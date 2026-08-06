import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { DEMO_MODE_STORAGE_KEY, DemoModeContext } from './demoMode'

/**
 * Demo Mode.
 *
 * Serves two distinct purposes, and the distinction matters:
 *
 * * **Explicitly enabled** — the user wants the enterprise sample catalogue
 *   even if the backend is healthy. Useful for demos where DataHub holds
 *   little data, or for showing the product with no infrastructure at all.
 * * **Automatic fallback** — the backend is unreachable, so services fall back
 *   on their own. That is handled per-service by `withFallback`, NOT here,
 *   because it is a property of a single failed call rather than a global mode.
 *
 * Both paths tag their data `demo` so the UI labels it either way. This
 * provider tracks only the deliberate choice.
 *
 * The preference persists to localStorage, and flipping it invalidates the
 * query cache so every panel refetches through the other path.
 */
export function DemoModeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [enabled, setEnabledState] = useState(
    () => localStorage.getItem(DEMO_MODE_STORAGE_KEY) === 'true',
  )

  useEffect(() => {
    localStorage.setItem(DEMO_MODE_STORAGE_KEY, String(enabled))
    // Cached entries came from the other data source, so they are all wrong
    // now. Invalidate rather than clear: mounted components keep showing the
    // previous value until the new one lands, instead of flashing empty.
    void queryClient.invalidateQueries()
  }, [enabled, queryClient])

  const setEnabled = useCallback((value: boolean) => setEnabledState(value), [])
  const toggle = useCallback(() => setEnabledState((current) => !current), [])

  const value = useMemo(
    () => ({ enabled, toggle, setEnabled }),
    [enabled, toggle, setEnabled],
  )

  return <DemoModeContext.Provider value={value}>{children}</DemoModeContext.Provider>
}
