import { PageHeader } from '@/components'

/** Upstream/downstream impact graph, rendered with React Flow. */
export function LineagePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Lineage"
        description="Upstream and downstream impact of a governance issue."
      />
      <p className="text-muted text-sm">
        Placeholder — the React Flow lineage graph is not implemented yet.
      </p>
    </div>
  )
}
