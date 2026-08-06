import { createContext, useContext } from 'react'

/**
 * Demo Mode context and helpers.
 *
 * Split from `DemoModeProvider.tsx` so that file exports only a component —
 * mixing components and plain values in one module disables React Fast
 * Refresh for the whole file, which costs a full reload on every edit.
 */

export const DEMO_MODE_STORAGE_KEY = 'dataguardian-demo-mode'

export interface DemoModeValue {
  /** True when the user has explicitly enabled Demo Mode. */
  enabled: boolean
  toggle: () => void
  setEnabled: (value: boolean) => void
}

export const DemoModeContext = createContext<DemoModeValue | null>(null)

export function useDemoMode(): DemoModeValue {
  const context = useContext(DemoModeContext)
  if (!context) {
    throw new Error('useDemoMode must be used inside <DemoModeProvider>')
  }
  return context
}

/**
 * Read the flag outside React.
 *
 * Services are plain functions called by React Query, so they cannot use the
 * hook. Reading localStorage directly keeps them in sync with the provider
 * without threading the flag through every call signature.
 */
export function isDemoModeEnabled(): boolean {
  return localStorage.getItem(DEMO_MODE_STORAGE_KEY) === 'true'
}
