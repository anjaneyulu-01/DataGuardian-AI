import { PageHeader } from '@/components'

/** Governance findings raised by the agent, with recommended remediation. */
export function IssuesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Issues"
        description="Governance findings detected by the agent, ranked by severity."
      />
      <p className="text-muted text-sm">
        Placeholder — detection rules and agent reasoning are not implemented yet.
      </p>
    </div>
  )
}
