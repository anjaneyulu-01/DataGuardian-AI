import {
  BookText,
  Bot,
  Boxes,
  Database,
  Home,
  Network,
  PlayCircle,
  Settings,
  ShieldCheck,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { NavLink } from 'react-router'

import { ShieldLogo } from './ShieldLogo'
import { cn } from '@/utils'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** Exact match — keeps the index route from staying always-active. */
  end?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Overview', icon: Home, end: true },
  { to: '/investigator', label: 'AI Investigator', icon: Bot },
  // Placed directly under the Investigator: it is the same capability with
  // the typing removed, and an evaluator should meet it before the
  // supporting pages.
  { to: '/judge-demo', label: 'Judge Demo', icon: PlayCircle },
  { to: '/governance', label: 'Governance', icon: ShieldCheck },
  { to: '/lineage', label: 'Lineage Explorer', icon: Network },
  { to: '/documentation', label: 'Documentation', icon: BookText },
  { to: '/risk', label: 'Risk Center', icon: TriangleAlert },
]

const FOOTER_ITEMS: NavItem[] = [
  { to: '/datahub', label: 'DataHub', icon: Database },
  { to: '/architecture', label: 'Architecture', icon: Boxes },
  { to: '/settings', label: 'Settings', icon: Settings },
]

/** Primary navigation rail. Collapses to icons below the lg breakpoint. */
export function Sidebar() {
  return (
    <aside className="border-line bg-surface/70 flex w-16 shrink-0 flex-col border-r backdrop-blur-sm lg:w-60">
      {/* Brand. */}
      <div className="flex h-14 items-center gap-2.5 px-3 lg:px-5">
        <ShieldLogo className="size-7 shrink-0" />
        <div className="hidden min-w-0 lg:block">
          <p className="text-ink truncate text-[13.5px] leading-tight font-semibold tracking-tight">
            DataGuardian AI
          </p>
          <p className="text-faint text-[10.5px] leading-tight">
            Metadata Governance Engineer
          </p>
        </div>
      </div>

      <nav className="mt-2 flex flex-1 flex-col gap-0.5 px-2 lg:px-3">
        {NAV_ITEMS.map((item) => (
          <SidebarLink key={item.to} item={item} />
        ))}
      </nav>

      <div className="border-line mb-3 border-t px-2 pt-3 lg:px-3">
        {FOOTER_ITEMS.map((item) => (
          <SidebarLink key={item.to} item={item} />
        ))}
      </div>
    </aside>
  )
}

function SidebarLink({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={item.label}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors lg:px-3',
          isActive
            ? 'bg-brand/12 text-ink'
            : 'text-muted hover:bg-raised hover:text-ink',
        )
      }
    >
      {({ isActive }) => (
        <>
          {/* Active indicator bar. */}
          <span
            aria-hidden
            className={cn(
              'bg-brand absolute top-1/2 left-0 h-4 w-0.5 -translate-y-1/2 rounded-full transition-opacity',
              isActive ? 'opacity-100' : 'opacity-0',
            )}
          />
          <Icon
            className={cn(
              'size-[18px] shrink-0 transition-colors',
              isActive ? 'text-brand-strong' : 'text-faint group-hover:text-muted',
            )}
            strokeWidth={2}
          />
          <span className="hidden truncate lg:inline">{item.label}</span>
        </>
      )}
    </NavLink>
  )
}
