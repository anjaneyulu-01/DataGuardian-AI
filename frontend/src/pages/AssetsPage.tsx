import { PageHeader } from '@/components'

/** Browsable inventory of DataHub metadata entities. */
export function AssetsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Assets"
        description="Datasets, dashboards, and pipelines catalogued in DataHub."
      />
      <p className="text-muted text-sm">
        Placeholder — the DataHub metadata integration is not implemented yet.
      </p>
    </div>
  )
}
