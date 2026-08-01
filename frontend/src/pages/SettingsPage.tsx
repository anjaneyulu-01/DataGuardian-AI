import { Bot, Database, Palette, ShieldCheck } from 'lucide-react'

import { Card, PageHeader, SectionHeader } from '@/components/ui'
import { useSystemStatus } from '@/hooks/useSystemStatus'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/utils'

/**
 * Workspace configuration. Connection state is real (from the backend);
 * the toggles are presentation until the scheduler and agent phases land.
 */
export function SettingsPage() {
  const status = useSystemStatus()
  const { theme, toggle } = useTheme()

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Settings"
        description="Connections, scanning behaviour, and workspace preferences."
      />

      <div className="space-y-6">
        {/* Connections — real status. */}
        <section>
          <SectionHeader title="Connections" description="Live status, polled every 30 seconds." />
          <Card className="divide-line divide-y p-0">
            <ConnectionRow
              icon={ShieldCheck}
              name="DataGuardian API"
              detail="FastAPI backend · http://localhost:8000"
              online={status.api === 'online'}
              checking={status.api === 'checking'}
            />
            <ConnectionRow
              icon={Database}
              name="DataHub"
              detail={
                status.datahubVersion
                  ? `GMS ${status.datahubVersion} · http://localhost:8080`
                  : 'GMS · http://localhost:8080'
              }
              online={status.datahub === 'online'}
              checking={status.datahub === 'checking'}
            />
          </Card>
        </section>

        {/* Agent behaviour — placeholders until the scheduler phase. */}
        <section>
          <SectionHeader
            title="Agent"
            description="Autonomy controls apply once the scheduled scanning phase ships."
          />
          <Card className="divide-line divide-y p-0">
            <ToggleRow
              icon={Bot}
              name="Scheduled scans"
              detail="Run a full governance scan every hour."
              enabled
            />
            <ToggleRow
              icon={ShieldCheck}
              name="Human-in-the-loop remediation"
              detail="Every write-back to DataHub requires explicit approval."
              enabled
              locked
            />
          </Card>
        </section>

        {/* Appearance. */}
        <section>
          <SectionHeader title="Appearance" />
          <Card className="p-0">
            <button
              type="button"
              onClick={toggle}
              className="flex w-full items-center gap-3.5 px-4 py-3.5 text-left"
            >
              <span className="border-line bg-raised text-muted grid size-9 place-items-center rounded-lg border">
                <Palette className="size-4" />
              </span>
              <span className="flex-1">
                <span className="text-ink block text-[13px] font-semibold">Theme</span>
                <span className="text-muted text-[12px]">
                  Currently {theme}. Click to switch.
                </span>
              </span>
              <ThemePreview active={theme === 'dark'} label="Dark" tone="dark" />
              <ThemePreview active={theme === 'light'} label="Light" tone="light" />
            </button>
          </Card>
        </section>
      </div>
    </div>
  )
}

function ConnectionRow({
  icon: Icon,
  name,
  detail,
  online,
  checking,
}: {
  icon: typeof Database
  name: string
  detail: string
  online: boolean
  checking: boolean
}) {
  return (
    <div className="flex items-center gap-3.5 px-4 py-3.5">
      <span className="border-line bg-raised text-muted grid size-9 place-items-center rounded-lg border">
        <Icon className="size-4" />
      </span>
      <div className="flex-1">
        <p className="text-ink text-[13px] font-semibold">{name}</p>
        <p className="text-muted text-[12px]">{detail}</p>
      </div>
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold',
          checking
            ? 'border-warning/25 bg-warning/10 text-warning'
            : online
              ? 'border-positive/25 bg-positive/10 text-positive'
              : 'border-critical/25 bg-critical/10 text-critical',
        )}
      >
        <span
          className={cn(
            'size-1.5 rounded-full',
            checking ? 'bg-warning animate-pulse' : online ? 'bg-positive' : 'bg-critical',
          )}
        />
        {checking ? 'Checking' : online ? 'Connected' : 'Offline'}
      </span>
    </div>
  )
}

function ToggleRow({
  icon: Icon,
  name,
  detail,
  enabled,
  locked,
}: {
  icon: typeof Bot
  name: string
  detail: string
  enabled?: boolean
  locked?: boolean
}) {
  return (
    <div className="flex items-center gap-3.5 px-4 py-3.5">
      <span className="border-line bg-raised text-muted grid size-9 place-items-center rounded-lg border">
        <Icon className="size-4" />
      </span>
      <div className="flex-1">
        <p className="text-ink text-[13px] font-semibold">
          {name}
          {locked ? (
            <span className="text-faint ml-2 text-[10.5px] font-medium tracking-wide uppercase">
              required
            </span>
          ) : null}
        </p>
        <p className="text-muted text-[12px]">{detail}</p>
      </div>
      <span
        aria-checked={enabled}
        role="switch"
        className={cn(
          'relative h-5 w-9 rounded-full transition-colors',
          enabled ? 'bg-brand' : 'bg-line-strong',
          locked && 'opacity-60',
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 size-4 rounded-full bg-white shadow transition-transform',
            enabled ? 'translate-x-4.5' : 'translate-x-0.5',
          )}
        />
      </span>
    </div>
  )
}

function ThemePreview({
  active,
  label,
  tone,
}: {
  active: boolean
  label: string
  tone: 'dark' | 'light'
}) {
  return (
    <span
      className={cn(
        'ml-2 grid h-9 w-14 place-items-end rounded-lg border p-1 text-[9px] font-semibold',
        tone === 'dark' ? 'bg-[oklch(18%_0.015_262)] text-white/70' : 'bg-white text-black/50',
        active ? 'border-brand shadow-glow' : 'border-line',
      )}
    >
      {label}
    </span>
  )
}
