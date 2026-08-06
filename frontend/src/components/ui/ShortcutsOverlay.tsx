import { AnimatePresence, motion } from 'framer-motion'
import { Keyboard, X } from 'lucide-react'
import { useEffect } from 'react'

import { SHORTCUTS } from '@/hooks/useKeyboardShortcuts'

interface ShortcutsOverlayProps {
  open: boolean
  onClose: () => void
}

/** Keyboard shortcut reference, opened with `?`. */
export function ShortcutsOverlay({ open, onClose }: ShortcutsOverlayProps) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={onClose}
          className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.96, y: 8 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.96, y: 8 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            role="dialog"
            aria-label="Keyboard shortcuts"
            onClick={(event) => event.stopPropagation()}
            className="card w-full max-w-md overflow-hidden p-0 shadow-pop"
          >
            <div className="border-line flex items-center gap-2 border-b px-5 py-3.5">
              <Keyboard className="text-brand-strong size-4" />
              <p className="text-ink text-[13px] font-semibold">Keyboard shortcuts</p>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="text-faint hover:text-ink ml-auto transition-colors"
              >
                <X className="size-4" />
              </button>
            </div>

            <ul className="max-h-[60vh] overflow-y-auto p-2">
              {SHORTCUTS.map((shortcut) => (
                <li
                  key={shortcut.keys}
                  className="flex items-center justify-between gap-4 px-3 py-2"
                >
                  <span className="text-ink-secondary text-[13px]">{shortcut.label}</span>
                  <span className="flex shrink-0 gap-1">
                    {shortcut.keys.split(' then ').map((key, index, all) => (
                      <span key={key} className="flex items-center gap-1">
                        <kbd className="border-line bg-raised text-muted rounded-md border px-1.5 py-0.5 font-mono text-[10.5px]">
                          {key}
                        </kbd>
                        {index < all.length - 1 ? (
                          <span className="text-faint text-[10px]">then</span>
                        ) : null}
                      </span>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
