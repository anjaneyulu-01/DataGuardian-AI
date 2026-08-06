import { Bot, Database, Palette, ShieldCheck, Sparkles } from 'lucide-react'

import {
  Card,
  PageHeader,
  SectionHeader,
  StatusIndicator,
  type ConnectionState,
} from '@/components/ui'
import { useApiHealth, useDataHubHealth, useLLMHealth } from '@/hooks/queries'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/utils'

/**
 * Workspace configuration.
 *
 * Connection state is real, polled from the backend. The agent toggles are
 * presentation until the scheduler phase, and are labelled as such rather than
 * implying they do something.
 */
export function SettingsPage() {
  const { theme, toggle } = useTheme()
  const api = useApiHealth()
  const datahub = useDataHubHealth()
  const llm = useLLMHealth()

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Settings"
        description="Connections, agent behaviour, and workspace preferences."
      />

      <div className="space-y-6">
        <section>
          <SectionHeader
            title="Connections"
            description="Live status, polled from the backend."
          />
          <Card className="divide-line divide-y p-0">
            <ConnectionRow
              icon={ShieldCheck}
              name="DataGuardian API"
              detail={
                api.data
                  ? `FastAPI v${api.data.version} · ${api.data.environment}`
                  : 'http://localhost:8000'
              }
              state={api.isPending ? 'checking' : api.isError ? 'offline' : 'online'}
            />
            <ConnectionRow
              icon={Database}
              name="DataHub"
              detail={
                datahub.data?.reachable
                  ? `GMS ${datahub.data.version ?? 'unknown'} · ${datahub.data.gms_url}`
                  : (datahub.data?.error ?? 'Not reachable')
              }
              state={
                datahub.isPending
                  ? 'checking'
                  : datahub.data?.reachable
                    ? 'online'
                    : 'offline'
              }
            />
            <ConnectionRow
              icon={Sparkles}
              name="AI Provider"
              detail={
                llm.data
                  ? `${llm.data.provider} · ${llm.data.model}${
                      llm.data.fallback_chain?.length
                        ? ` · fallback: ${llm.data.fallback_chain.join(', ')}`
                        : ''
                    }`
                  : 'Checking provider…'
              }
              state={
                llm.isPending
                  ? 'checking'
                  : !llm.data?.configured
                    ? 'unconfigured'
                    : llm.data.reachable
                      ? 'online'
                      : 'offline'
              }
            />
          </Card>
          {llm.data && !llm.data.configured ? (
            <p className="text-muted mt-2 text-[12px]">
              Set an API key in the <code className="text-ink-secondary">.env</code> at
              the repository root to enable AI features.
            </p>
          ) : null}
        </section>

        <section>
          <SectionHeader
            title="Agent"
            description="Autonomy controls apply once scheduled scanning ships."
          />
          <Card className="divide-line divide-y p-0">
            <ToggleRow
              icon={Bot}
              name="Scheduled scans"
              detail="Run a full governance scan every hour."
              enabled={false}
              pending
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
              <ThemeSwatch active={theme === 'dark'} label="Dark" tone="dark" />
              <ThemeSwatch active={theme === 'light'} label="Light" tone="light" />
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
  state,
}: {
  icon: typeof Database
  name: string
  detail: string
  state: ConnectionState
}) {
  return (
    <div className="flex items-center gap-3.5 px-4 py-3.5">
      <span className="border-line bg-raised text-muted grid size-9 shrink-0 place-items-center rounded-lg border">
        <Icon className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-ink text-[13px] font-semibold">{name}</p>
        <p className="text-muted truncate text-[12px]">{detail}</p>
      </div>
      <StatusIndicator label={name} state={state} detail={detail} compact />
    </div>
  )
}

function ToggleRow({
  icon: Icon,
  name,
  detail,
  enabled,
  locked,
  pending,
}: {
  icon: typeof Bot
  name: string
  detail: string
  enabled?: boolean
  locked?: boolean
  pending?: boolean
}) {
  return (
    <div className="flex items-center gap-3.5 px-4 py-3.5">
      <span className="border-line bg-raised text-muted grid size-9 shrink-0 place-items-center rounded-lg border">
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
          {pending ? (
            <span className="text-warning ml-2 text-[10.5px] font-medium tracking-wide uppercase">
              coming soon
            </span>
          ) : null}
        </p>
        <p className="text-muted text-[12px]">{detail}</p>
      </div>
      <span
        role="switch"
        aria-checked={Boolean(enabled)}
        aria-disabled={locked || pending}
        className={cn(
          'relative h-5 w-9 shrink-0 rounded-full transition-colors',
          enabled ? 'bg-brand' : 'bg-line-strong',
          (locked || pending) && 'opacity-60',
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

function ThemeSwatch({
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
        tone === 'dark'
          ? 'bg-[oklch(18%_0.015_262)] text-white/70'
          : 'bg-white text-black/50',
        active ? 'border-brand shadow-glow' : 'border-line',
      )}
    >
      {label}
    </span>
  )
}
