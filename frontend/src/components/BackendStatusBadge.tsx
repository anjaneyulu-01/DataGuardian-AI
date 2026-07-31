import { useBackendStatus } from '@/hooks/useBackendStatus'
import { cn } from '@/utils'

/**
 * Shows whether the FastAPI backend is reachable from the browser.
 * Kept in the shell so a broken local setup is obvious at a glance.
 */
export function BackendStatusBadge() {
  const status = useBackendStatus()

  const label =
    status.state === 'loading'
      ? 'Connecting…'
      : status.state === 'ready'
        ? `API ${status.health.status}`
        : 'API unreachable'

  const tone =
    status.state === 'loading'
      ? 'bg-line text-muted'
      : status.state === 'ready'
        ? 'bg-severity-low/15 text-severity-low'
        : 'bg-severity-critical/15 text-severity-critical'

  return (
    <span
      title={status.state === 'error' ? status.message : undefined}
      className={cn('rounded-full px-3 py-1 text-xs font-medium', tone)}
    >
      {label}
    </span>
  )
}
