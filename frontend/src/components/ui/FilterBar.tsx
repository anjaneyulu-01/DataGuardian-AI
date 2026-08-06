import { X } from 'lucide-react'

import { cn } from '@/utils'

export interface FilterOption<T extends string = string> {
  value: T
  label: string
  /** Rendered as a trailing count chip. */
  count?: number
}

interface FilterBarProps<T extends string> {
  options: FilterOption<T>[]
  value: T
  onChange: (value: T) => void
  /** Shown when `value` differs from the first option. */
  onClear?: () => void
  label?: string
  className?: string
}

/**
 * Segmented single-select filter.
 *
 * Buttons rather than a `<select>`: the option set is small and always
 * visible, so the current filter and the alternatives are readable without a
 * click — which matters when the filter changes what a governance number
 * means.
 */
export function FilterBar<T extends string>({
  options,
  value,
  onChange,
  onClear,
  label,
  className,
}: FilterBarProps<T>) {
  const isDefault = options[0]?.value === value

  return (
    <div className={cn('flex flex-wrap items-center gap-1.5', className)} role="group" aria-label={label}>
      {label ? (
        <span className="text-faint mr-1 text-[11px] font-medium tracking-wide uppercase">
          {label}
        </span>
      ) : null}

      {options.map((option) => {
        const isActive = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            aria-pressed={isActive}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors',
              isActive
                ? 'border-brand/40 bg-brand/12 text-ink'
                : 'border-line bg-surface text-muted hover:text-ink',
            )}
          >
            {option.label}
            {option.count !== undefined ? (
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.5 text-[10px] tabular-nums',
                  isActive ? 'bg-brand/20 text-brand-strong' : 'bg-raised text-faint',
                )}
              >
                {option.count}
              </span>
            ) : null}
          </button>
        )
      })}

      {onClear && !isDefault ? (
        <button
          type="button"
          onClick={onClear}
          className="text-faint hover:text-ink ml-1 inline-flex items-center gap-1 text-[11.5px] transition-colors"
        >
          <X className="size-3" /> Clear
        </button>
      ) : null}
    </div>
  )
}
