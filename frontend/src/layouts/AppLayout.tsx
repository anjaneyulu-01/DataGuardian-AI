import { AnimatePresence, motion } from 'framer-motion'
import { FlaskConical } from 'lucide-react'
import { useCallback, useState } from 'react'
import { Outlet, useLocation } from 'react-router'

import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { useDemoMode } from '@/app/demoMode'
import { ShortcutsOverlay } from '@/components/ui/ShortcutsOverlay'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'

/**
 * App shell: sidebar rail, glass top bar, routed content.
 *
 * Route changes cross-fade so navigation feels continuous rather than like a
 * page load.
 */
export function AppLayout() {
  const { pathname } = useLocation()
  const demo = useDemoMode()
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  const showHelp = useCallback(() => setShortcutsOpen(true), [])
  useKeyboardShortcuts(showHelp)

  return (
    <div className="flex h-full">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />

        {/* Demo Mode is a persistent, unmissable band. A viewer must never be
            able to mistake the sample catalogue for their own data. */}
        <AnimatePresence>
          {demo.enabled ? (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-warning/25 bg-warning/10 overflow-hidden border-b"
            >
              <div className="mx-auto flex w-full max-w-[1400px] items-center gap-2 px-4 py-2 sm:px-6">
                <FlaskConical className="text-warning size-3.5 shrink-0" />
                <p className="text-warning text-[12px] font-medium">
                  Demo Mode — showing a sample enterprise catalogue, not your DataHub
                  instance.
                </p>
                <button
                  type="button"
                  onClick={() => demo.setEnabled(false)}
                  className="text-warning ml-auto shrink-0 text-[11.5px] font-semibold underline underline-offset-2"
                >
                  Switch to live data
                </button>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>

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

      <ShortcutsOverlay open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  )
}
