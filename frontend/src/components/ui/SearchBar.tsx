import { Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { cn } from '@/utils'

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  /** Debounce in ms before `onChange` fires. 0 disables it. */
  debounceMs?: number
  className?: string
}

/**
 * Debounced search input.
 *
 * Debouncing lives here rather than in each page: the Governance table is
 * backed by a network call, and firing one per keystroke would hammer both
 * our API and DataHub. Local state keeps typing responsive while the
 * committed value trails behind.
 */
export function SearchBar({
  value,
  onChange,
  placeholder = 'Search…',
  debounceMs = 300,
  className,
}: SearchBarProps) {
  const [draft, setDraft] = useState(value)

  // Re-sync when the parent resets the value (e.g. "clear filters").
  useEffect(() => {
    setDraft(value)
  }, [value])

  useEffect(() => {
    if (draft === value) return
    if (debounceMs === 0) {
      onChange(draft)
      return
    }
    const timer = setTimeout(() => onChange(draft), debounceMs)
    return () => clearTimeout(timer)
    // `value` is intentionally excluded: including it would restart the timer
    // when the parent echoes the committed value back.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft, debounceMs])

  return (
    <label
      className={cn(
        'card focus-within:shadow-glow flex items-center gap-2.5 px-3.5 py-2 transition-shadow',
        className,
      )}
    >
      <Search className="text-faint size-4 shrink-0" />
      <input
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="text-ink placeholder:text-faint w-full bg-transparent text-[13px] outline-none"
      />
      {draft ? (
        <button
          type="button"
          onClick={() => {
            setDraft('')
            onChange('')
          }}
          aria-label="Clear search"
          className="text-faint hover:text-ink shrink-0 transition-colors"
        >
          <X className="size-3.5" />
        </button>
      ) : null}
    </label>
  )
}
