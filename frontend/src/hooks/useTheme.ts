import { useCallback, useEffect, useState } from 'react'

type Theme = 'dark' | 'light'

const STORAGE_KEY = 'dataguardian-theme'

/**
 * Theme toggle backed by `data-theme` on <html>.
 *
 * Every color in the app is a semantic CSS variable keyed off that attribute
 * (see index.css), so this hook is the only theme-aware JavaScript.
 * Dark is the default — it is the product surface.
 */
export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' ? 'light' : 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const toggle = useCallback(() => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, toggle }
}
