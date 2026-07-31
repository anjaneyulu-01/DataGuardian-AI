import { Route, Routes } from 'react-router'

import { AppLayout } from '@/layouts'
import {
  AssetsPage,
  DashboardPage,
  IssuesPage,
  LineagePage,
  NotFoundPage,
} from '@/pages'

/** Route table. Every page renders inside the persistent app shell. */
function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="assets" element={<AssetsPage />} />
        <Route path="issues" element={<IssuesPage />} />
        <Route path="lineage" element={<LineagePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
