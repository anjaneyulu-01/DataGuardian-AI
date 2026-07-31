import { PageHeader } from '@/components'

/** Landing view. Governance KPIs and Recharts panels land here. */
export function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Governance posture across the connected DataHub instance."
      />
      <p className="text-muted text-sm">
        Placeholder — metrics, trend charts, and agent activity are not implemented yet.
      </p>
    </div>
  )
}
