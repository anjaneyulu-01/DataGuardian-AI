import { cn } from '@/utils'

interface LoadingStateProps {
  /** "thinking" renders the AI dots + label; "skeleton" renders shimmer bars. */
  variant?: 'thinking' | 'skeleton'
  label?: string
  /** Number of skeleton rows. */
  rows?: number
  className?: string
}

/** Loading affordances: AI "thinking" indicator and content skeletons. */
export function LoadingState({
  variant = 'skeleton',
  label = 'DataGuardian is investigating…',
  rows = 3,
  className,
}: LoadingStateProps) {
  if (variant === 'thinking') {
    return (
      <div className={cn('card flex items-center gap-3 px-5 py-4', className)}>
        <span className="flex gap-1">
          {[0, 1, 2].map((index) => (
            <span
              key={index}
              className="bg-brand size-1.5 animate-bounce rounded-full"
              style={{ animationDelay: `${index * 0.15}s`, animationDuration: '0.9s' }}
            />
          ))}
        </span>
        <p className="text-muted text-[13px]">{label}</p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)} aria-busy>
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="bg-raised h-4 animate-pulse rounded-md"
          style={{ width: `${100 - index * 12}%`, animationDelay: `${index * 0.1}s` }}
        />
      ))}
    </div>
  )
}
