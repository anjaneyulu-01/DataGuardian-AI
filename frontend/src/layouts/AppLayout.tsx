import { NavLink, Outlet } from 'react-router'

import { BackendStatusBadge } from '@/components'
import { cn } from '@/utils'

interface NavItem {
  to: string
  label: string
  /** Match the path exactly — needed so the index route is not always active. */
  end?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/assets', label: 'Assets' },
  { to: '/issues', label: 'Issues' },
  { to: '/lineage', label: 'Lineage' },
]

/** Persistent chrome — sidebar navigation plus the routed page outlet. */
export function AppLayout() {
  return (
    <div className="flex h-full">
      <aside className="border-line bg-surface flex w-60 shrink-0 flex-col border-r">
        <div className="border-line border-b px-5 py-4">
          <p className="text-ink text-sm font-semibold">DataGuardian AI</p>
          <p className="text-muted text-xs">Autonomous governance agent</p>
        </div>

        <nav className="flex flex-col gap-1 p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-brand/15 text-brand font-medium'
                    : 'text-muted hover:bg-line/50 hover:text-ink',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-line flex h-14 shrink-0 items-center justify-end border-b px-6">
          <BackendStatusBadge />
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
