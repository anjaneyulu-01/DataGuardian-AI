import { cn } from '@/utils'

type SkeletonVariant = 'text' | 'card' | 'metric' | 'table' | 'chart'

interface LoadingSkeletonProps {
  variant?: SkeletonVariant
  /** Rows for `text` and `table`; cards for `metric`. */
  count?: number
  className?: string
}

/**
 * Shape-matched loading placeholders.
 *
 * Each variant mirrors the layout of the component it replaces, so content
 * does not jump when it arrives. A generic grey box would reflow the page on
 * every load, which reads as slower even when it is not.
 */
export function LoadingSkeleton({
  variant = 'text',
  count = 3,
  className,
}: LoadingSkeletonProps) {
  const shimmer = 'animate-pulse rounded-md bg-raised'

  if (variant === 'metric') {
    return (
      <div
        className={cn('grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5', className)}
        aria-busy
      >
        {Array.from({ length: count }, (_, index) => (
          <div key={index} className="card p-5">
            <div className={cn(shimmer, 'h-3 w-20')} />
            <div className={cn(shimmer, 'mt-4 h-7 w-16')} />
            <div className={cn(shimmer, 'mt-3 h-3 w-24')} />
          </div>
        ))}
      </div>
    )
  }

  if (variant === 'table') {
    return (
      <div className={cn('card overflow-hidden', className)} aria-busy>
        <div className="border-line flex gap-4 border-b px-4 py-3">
          {Array.from({ length: 5 }, (_, index) => (
            <div key={index} className={cn(shimmer, 'h-3 flex-1')} />
          ))}
        </div>
        {Array.from({ length: count }, (_, row) => (
          <div key={row} className="border-line flex gap-4 border-b px-4 py-3.5 last:border-0">
            {Array.from({ length: 5 }, (_, col) => (
              <div
                key={col}
                className={cn(shimmer, 'h-4 flex-1')}
                style={{ animationDelay: `${(row * 5 + col) * 0.03}s` }}
              />
            ))}
          </div>
        ))}
      </div>
    )
  }

  if (variant === 'chart') {
    return (
      <div className={cn('card p-5', className)} aria-busy>
        <div className={cn(shimmer, 'h-3 w-32')} />
        <div className="mt-6 flex h-48 items-end gap-2">
          {Array.from({ length: 12 }, (_, index) => (
            <div
              key={index}
              className={cn(shimmer, 'flex-1')}
              style={{
                height: `${35 + Math.sin(index) * 30 + 25}%`,
                animationDelay: `${index * 0.05}s`,
              }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (variant === 'card') {
    return (
      <div className={cn('space-y-4', className)} aria-busy>
        {Array.from({ length: count }, (_, index) => (
          <div key={index} className="card p-5">
            <div className={cn(shimmer, 'h-4 w-40')} />
            <div className={cn(shimmer, 'mt-3 h-3 w-full')} />
            <div className={cn(shimmer, 'mt-2 h-3 w-4/5')} />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)} aria-busy>
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className={cn(shimmer, 'h-4')}
          style={{ width: `${100 - index * 12}%`, animationDelay: `${index * 0.08}s` }}
        />
      ))}
    </div>
  )
}
