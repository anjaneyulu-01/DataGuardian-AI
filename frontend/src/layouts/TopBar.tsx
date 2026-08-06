import { Bell, ChevronDown, FlaskConical, Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { useLocation } from 'react-router'

import {
  NotificationsPanel,
  StatusIndicator,
  type ConnectionState,
} from '@/components/ui'
import { useDemoMode } from '@/app/demoMode'
import {
  useActivity,
  useApiHealth,
  useDataHubHealth,
  useLLMHealth,
  useViolations,
} from '@/hooks/queries'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/utils'
import { notificationCount } from '@/utils/notifications'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Overview',
  '/investigator': 'AI Investigator',
  '/governance': 'Governance',
  '/lineage': 'Lineage Explorer',
  '/documentation': 'Documentation',
  '/risk': 'Risk Center',
  '/architecture': 'Architecture',
  '/settings': 'Settings',
}

/**
 * Glass top bar: workspace, five live status indicators, Demo Mode, alerts,
 * theme, profile.
 *
 * The indicators are real, polled from the backend, and are the fastest way
 * to tell whether an empty panel means "no findings" or "nothing connected".
 */
export function TopBar() {
  const { pathname } = useLocation()
  const { theme, toggle } = useTheme()
  const demo = useDemoMode()
  const [notificationsOpen, setNotificationsOpen] = useState(false)

  const api = useApiHealth()
  const datahub = useDataHubHealth()
  const llm = useLLMHealth()
  const activity = useActivity()
  const violations = useViolations()

  const alertCount = notificationCount(violations.data?.data ?? [])
  const cache = datahub.data?.cache

  return (
    <header className="glass sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-4 px-4 lg:px-6">
      <div className="flex min-w-0 items-center gap-2.5">
        <h1 className="text-ink truncate text-[14px] font-semibold tracking-tight">
          {PAGE_TITLES[pathname] ?? 'DataGuardian AI'}
        </h1>
        <span className="text-faint hidden text-[12px] sm:inline">/</span>
        <button
          type="button"
          className="text-muted hover:text-ink hidden items-center gap-1 text-[12px] transition-colors sm:inline-flex"
          title="Workspace"
        >
          Production
          <ChevronDown className="size-3" />
        </button>
      </div>

      <div className="flex items-center gap-2">
        {/* Five dependency indicators. Progressively hidden on narrow screens,
            most important last to disappear. */}
        <StatusIndicator
          label="Backend"
          state={api.isPending ? 'checking' : api.isError ? 'offline' : 'online'}
          detail={api.data ? `v${api.data.version} · ${api.data.environment}` : undefined}
          className="hidden sm:inline-flex"
        />
        <StatusIndicator
          label="DataHub"
          state={
            datahub.isPending
              ? 'checking'
              : datahub.data?.reachable
                ? 'online'
                : 'offline'
          }
          detail={
            datahub.data?.reachable
              ? `GMS ${datahub.data.version ?? 'unknown'}`
              : (datahub.data?.error ?? 'Unreachable')
          }
          className="hidden sm:inline-flex"
        />
        <StatusIndicator
          label="LLM"
          state={
            llm.isPending
              ? 'checking'
              : llm.isError
                ? 'offline'
                : !llm.data?.configured
                  ? 'unconfigured'
                  : llm.data.reachable
                    ? 'online'
                    : 'offline'
          }
          detail={llm.data ? `${llm.data.provider} · ${llm.data.model}` : undefined}
          className="hidden lg:inline-flex"
        />
        <StatusIndicator
          label="Cache"
          // The cache is a property of a reachable backend, so it inherits
          // DataHub's connectivity rather than having its own probe.
          state={cache ? 'online' : datahub.isPending ? 'checking' : 'unconfigured'}
          detail={
            cache
              ? `${cache.entries} entries · ${Math.round(cache.hit_rate * 100)}% hit rate`
              : 'No cache statistics yet'
          }
          className="hidden xl:inline-flex"
        />
        <StatusIndicator
          label="Scheduler"
          state={
            api.isPending
              ? 'checking'
              : api.data?.scheduler_enabled
                ? 'online'
                : 'unconfigured'
          }
          detail={
            api.data?.scheduler_enabled
              ? 'Background scans running'
              : 'Disabled (SCHEDULER_ENABLED=false)'
          }
          className="hidden xl:inline-flex"
        />

        <span className="bg-line mx-1 hidden h-5 w-px sm:block" />

        {/* Demo Mode. Deliberately prominent — a viewer must always be able to
            tell whether they are looking at real metadata. */}
        <button
          type="button"
          onClick={demo.toggle}
          aria-pressed={demo.enabled}
          title={
            demo.enabled
              ? 'Demo Mode is on — showing the sample enterprise catalogue'
              : 'Switch to the sample enterprise catalogue'
          }
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition-colors',
            demo.enabled
              ? 'border-warning/40 bg-warning/15 text-warning'
              : 'border-line bg-surface/70 text-muted hover:text-ink',
          )}
        >
          <FlaskConical className="size-3" />
          <span className="hidden sm:inline">Demo</span>
        </button>

        <div className="relative">
          <IconButton
            label="Notifications"
            onClick={() => setNotificationsOpen((open) => !open)}
          >
            <Bell className="size-4" />
            {alertCount > 0 ? (
              <span className="bg-critical absolute top-0.5 right-0.5 grid min-w-4 place-items-center rounded-full px-1 text-[9px] font-bold text-white">
                {alertCount > 9 ? '9+' : alertCount}
              </span>
            ) : null}
          </IconButton>

          <NotificationsPanel
            open={notificationsOpen}
            onClose={() => setNotificationsOpen(false)}
            activity={activity.data?.data ?? []}
            findings={violations.data?.data ?? []}
            source={violations.data?.source ?? 'demo'}
            reason={violations.data?.reason}
          />
        </div>

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

export type { ConnectionState }
