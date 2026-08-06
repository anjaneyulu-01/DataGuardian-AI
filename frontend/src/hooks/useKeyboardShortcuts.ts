import { useEffect } from 'react'
import { useNavigate } from 'react-router'

import { useDemoMode } from '@/app/demoMode'
import { useTheme } from '@/hooks/useTheme'

/** Shortcuts, in the order they appear in the help overlay. */
export const SHORTCUTS: { keys: string; label: string }[] = [
  { keys: 'G then O', label: 'Overview' },
  { keys: 'G then I', label: 'AI Investigator' },
  { keys: 'G then G', label: 'Governance' },
  { keys: 'G then L', label: 'Lineage Explorer' },
  { keys: 'G then D', label: 'Documentation' },
  { keys: 'G then R', label: 'Risk Center' },
  { keys: 'G then A', label: 'Architecture' },
  { keys: 'G then S', label: 'Settings' },
  { keys: '/', label: 'Ask DataGuardian' },
  { keys: 'D', label: 'Toggle Demo Mode' },
  { keys: 'T', label: 'Toggle theme' },
  { keys: '?', label: 'Show this help' },
]

const ROUTES: Record<string, string> = {
  o: '/',
  i: '/investigator',
  g: '/governance',
  l: '/lineage',
  d: '/documentation',
  r: '/risk',
  a: '/architecture',
  s: '/settings',
}

/** How long a `g` prefix stays armed before it expires. */
const CHORD_WINDOW_MS = 1200

/**
 * Global keyboard shortcuts, in the Linear/GitHub idiom.
 *
 * Two rules that make shortcuts feel right rather than hostile:
 *
 * * **Never fire while typing.** Any keystroke inside an input, textarea, or
 *   contentEditable is the user's text, not a command.
 * * **Chords expire.** Pressing `g` and wandering off should not leave the
 *   app waiting indefinitely for a second key.
 */
export function useKeyboardShortcuts(onShowHelp: () => void): void {
  const navigate = useNavigate()
  const { toggle: toggleTheme } = useTheme()
  const demo = useDemoMode()

  useEffect(() => {
    let chordArmed = false
    let chordTimer: number | undefined

    const disarm = () => {
      chordArmed = false
      window.clearTimeout(chordTimer)
    }

    const onKeyDown = (event: KeyboardEvent) => {
      // Let the browser and the OS keep their own combinations.
      if (event.metaKey || event.ctrlKey || event.altKey) return

      const target = event.target as HTMLElement | null
      const isTyping =
        target?.isContentEditable ||
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(target?.tagName ?? '')

      if (isTyping) {
        // `Escape` from a field is a universal "give me back the page".
        if (event.key === 'Escape') target?.blur()
        return
      }

      const key = event.key.toLowerCase()

      // Second key of a `g …` chord.
      if (chordArmed) {
        disarm()
        const route = ROUTES[key]
        if (route) {
          event.preventDefault()
          navigate(route)
        }
        return
      }

      if (key === 'g') {
        chordArmed = true
        chordTimer = window.setTimeout(disarm, CHORD_WINDOW_MS)
        return
      }

      if (key === '/') {
        // Jump to the Investigator and focus its prompt.
        event.preventDefault()
        navigate('/investigator')
        // Defer until the route has painted its input.
        window.setTimeout(() => {
          document
            .querySelector<HTMLInputElement>('input[aria-label="Ask DataGuardian"]')
            ?.focus()
        }, 120)
        return
      }

      if (key === 'd') {
        event.preventDefault()
        demo.toggle()
        return
      }

      if (key === 't') {
        event.preventDefault()
        toggleTheme()
        return
      }

      if (key === '?') {
        event.preventDefault()
        onShowHelp()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      disarm()
    }
  }, [navigate, toggleTheme, demo, onShowHelp])
}
