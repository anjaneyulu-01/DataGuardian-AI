import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

/**
 * React Query configuration.
 *
 * Created inside a `useState` initialiser rather than at module scope so it is
 * not shared across renders in development's StrictMode double-mount, and so
 * tests can mount an isolated cache per test.
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Services already fall back to demo data on failure, so an
            // aggressive retry only delays showing the user something.
            retry: 1,
            retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
            // Refetching on every tab focus is noise for a governance
            // dashboard whose data changes on an ingestion cadence.
            refetchOnWindowFocus: false,
            staleTime: 30_000,
          },
          mutations: { retry: false },
        },
      }),
  )

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
