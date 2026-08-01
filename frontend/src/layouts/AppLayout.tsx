import { AnimatePresence, motion } from 'framer-motion'
import { Outlet, useLocation } from 'react-router'

import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

/**
 * App shell: sidebar rail + glass topbar + routed content.
 * Route changes cross-fade so navigation feels continuous.
 */
export function AppLayout() {
  const { pathname } = useLocation()

  return (
    <div className="flex h-full">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />

        <main className="min-h-0 flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
              className="mx-auto w-full max-w-[1400px] p-4 sm:p-6"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
