import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router'

import { LoadingState } from '@/components/ui'
import { AppLayout } from '@/layouts'
import {
  DocumentationPage,
  GovernancePage,
  InvestigatorPage,
  NotFoundPage,
  OverviewPage,
  SettingsPage,
} from '@/pages'

// Route-split the two pages that carry heavy chart/graph libraries, so the
// initial bundle ships without React Flow and Recharts.
const LineagePage = lazy(() =>
  import('@/pages/LineagePage').then((m) => ({ default: m.LineagePage })),
)
const RiskCenterPage = lazy(() =>
  import('@/pages/RiskCenterPage').then((m) => ({ default: m.RiskCenterPage })),
)

/** Route table. Every page renders inside the persistent workspace shell. */
function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="investigator" element={<InvestigatorPage />} />
        <Route path="governance" element={<GovernancePage />} />
        <Route
          path="lineage"
          element={
            <Suspense fallback={<LoadingState rows={5} className="pt-8" />}>
              <LineagePage />
            </Suspense>
          }
        />
        <Route path="documentation" element={<DocumentationPage />} />
        <Route
          path="risk"
          element={
            <Suspense fallback={<LoadingState rows={5} className="pt-8" />}>
              <RiskCenterPage />
            </Suspense>
          }
        />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
