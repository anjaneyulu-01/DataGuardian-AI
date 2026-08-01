import { Bell, Moon, Sun } from 'lucide-react'
import { useLocation } from 'react-router'

import { useSystemStatus, type LinkState } from '@/hooks/useSystemStatus'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/utils'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Overview',
  '/investigator': 'AI Investigator',
  '/governance': 'Governance',
  '/lineage': 'Lineage Explorer',
  '/documentation': 'Documentation',
  '/risk': 'Risk Center',
  '/settings': 'Settings',
}

/**
 * Glass topbar: current page, live API + DataHub status (real, polled from
 * the backend — the only non-mock data in the shell), notifications, theme
 * toggle, avatar.
 */
export function TopBar() {
  const { pathname } = useLocation()
  const status = useSystemStatus()
  const { theme, toggle } = useTheme()

  return (
    <header className="glass sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-4 px-4 lg:px-6">
      <div className="flex min-w-0 items-baseline gap-2.5">
        <h1 className="text-ink truncate text-[14px] font-semibold tracking-tight">
          {PAGE_TITLES[pathname] ?? 'DataGuardian AI'}
        </h1>
      </div>

      <div className="flex items-center gap-2">
        <StatusPill label="API" state={status.api} />
        <StatusPill
          label="DataHub"
          state={status.datahub}
          title={status.datahubVersion ?? undefined}
        />

        <span className="bg-line mx-1 hidden h-5 w-px sm:block" />

        <IconButton label="Notifications">
          <Bell className="size-4" />
          <span className="bg-brand absolute top-1.5 right-1.5 size-1.5 rounded-full" />
        </IconButton>

        <IconButton label="Toggle theme" onClick={toggle}>
          {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </IconButton>

        <button
          type="button"
          aria-label="Account"
          className="from-brand to-accent ml-1 grid size-8 shrink-0 place-items-center rounded-full bg-gradient-to-br text-[11px] font-bold text-white shadow-card"
        >
          AJ
        </button>
      </div>
    </header>
  )
}

function StatusPill({
  label,
  state,
  title,
}: {
  label: string
  state: LinkState
  title?: string
}) {
  return (
    <span
      title={title}
      className="border-line bg-surface/70 hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium sm:inline-flex"
    >
      <span
        className={cn(
          'size-1.5 rounded-full',
          state === 'online' && 'bg-positive',
          state === 'offline' && 'bg-critical',
          state === 'checking' && 'bg-warning animate-pulse',
        )}
      />
      <span className="text-muted">{label}</span>
    </span>
  )
}

function IconButton({
  label,
  onClick,
  children,
}: {
  label: string
  onClick?: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="text-muted hover:bg-raised hover:text-ink relative grid size-8 place-items-center rounded-lg transition-colors"
    >
      {children}
    </button>
  )
}
