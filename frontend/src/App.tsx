import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router'

import { ErrorBoundary } from '@/app/ErrorBoundary'
import { LoadingSkeleton } from '@/components/ui'
import { AppLayout } from '@/layouts'
import { OverviewPage } from '@/pages'

/**
 * Route-split every page except the landing one.
 *
 * Overview stays in the main bundle because it is the first paint — lazily
 * loading it would add a network round-trip to the very first thing a user
 * sees. Everything else loads on navigation, keeping React Flow, Recharts,
 * and the Architecture page's content out of the initial download.
 */
const InvestigatorPage = lazy(() =>
  import('@/pages/InvestigatorPage').then((m) => ({ default: m.InvestigatorPage })),
)
const GovernancePage = lazy(() =>
  import('@/pages/GovernancePage').then((m) => ({ default: m.GovernancePage })),
)
const LineagePage = lazy(() =>
  import('@/pages/LineagePage').then((m) => ({ default: m.LineagePage })),
)
const DocumentationPage = lazy(() =>
  import('@/pages/DocumentationPage').then((m) => ({ default: m.DocumentationPage })),
)
const RiskCenterPage = lazy(() =>
  import('@/pages/RiskCenterPage').then((m) => ({ default: m.RiskCenterPage })),
)
const ArchitecturePage = lazy(() =>
  import('@/pages/ArchitecturePage').then((m) => ({ default: m.ArchitecturePage })),
)
const DataHubPage = lazy(() =>
  import('@/pages/DataHubPage').then((m) => ({ default: m.DataHubPage })),
)
const JudgeDemoPage = lazy(() =>
  import('@/pages/JudgeDemoPage').then((m) => ({ default: m.JudgeDemoPage })),
)
const SettingsPage = lazy(() =>
  import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)
const NotFoundPage = lazy(() =>
  import('@/pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })),
)

/**
 * Wrap a lazy page in its own Suspense and ErrorBoundary.
 *
 * Per-page boundaries mean a crash in the Lineage graph leaves the sidebar,
 * top bar, and every other route usable — the workspace degrades rather than
 * going blank.
 */
function Page({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSkeleton variant="card" count={3} className="pt-4" />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route
          path="investigator"
          element={
            <Page>
              <InvestigatorPage />
            </Page>
          }
        />
        <Route
          path="governance"
          element={
            <Page>
              <GovernancePage />
            </Page>
          }
        />
        <Route
          path="lineage"
          element={
            <Page>
              <LineagePage />
            </Page>
          }
        />
        <Route
          path="documentation"
          element={
            <Page>
              <DocumentationPage />
            </Page>
          }
        />
        <Route
          path="risk"
          element={
            <Page>
              <RiskCenterPage />
            </Page>
          }
        />
        <Route
          path="datahub"
          element={
            <Page>
              <DataHubPage />
            </Page>
          }
        />
        <Route
          path="judge-demo"
          element={
            <Page>
              <JudgeDemoPage />
            </Page>
          }
        />
        <Route
          path="architecture"
          element={
            <Page>
              <ArchitecturePage />
            </Page>
          }
        />
        <Route
          path="settings"
          element={
            <Page>
              <SettingsPage />
            </Page>
          }
        />
        <Route
          path="*"
          element={
            <Page>
              <NotFoundPage />
            </Page>
          }
        />
      </Route>
    </Routes>
  )
}

export default App
