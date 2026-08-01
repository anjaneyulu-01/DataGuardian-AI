import { Search, ShieldCheck, UserX } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Card, EmptyState, PageHeader, StatusBadge } from '@/components/ui'
import { governanceAssets } from '@/data/mockData'
import type { GovernanceAsset, Severity } from '@/types/domain'
import { cn } from '@/utils'
import { timeAgo } from '@/utils/format'
import { SEVERITY, SEVERITY_ORDER } from '@/utils/severity'

type SeverityFilter = Severity | 'all'

/** Catalogue table with search, severity filters, and per-metric bars. */
export function GovernancePage() {
  const [query, setQuery] = useState('')
  const [severity, setSeverity] = useState<SeverityFilter>('all')

  const filtered = useMemo(() => {
    const lowered = query.trim().toLowerCase()
    return governanceAssets.filter((asset) => {
      if (severity !== 'all' && asset.severity !== severity) return false
      if (!lowered) return true
      return [asset.name, asset.platform, asset.domain, asset.owner ?? '']
        .join(' ')
        .toLowerCase()
        .includes(lowered)
    })
  }, [query, severity])

  return (
    <div>
      <PageHeader
        title="Governance"
        description="Every catalogued asset scored on coverage, documentation, and composite health."
      />

      {/* Controls. */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="card focus-within:shadow-glow flex min-w-56 flex-1 items-center gap-2.5 px-3.5 py-2 transition-shadow sm:max-w-xs">
          <Search className="text-faint size-4 shrink-0" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search assets, owners, domains…"
            className="text-ink placeholder:text-faint w-full bg-transparent text-[13px] outline-none"
            aria-label="Search assets"
          />
        </label>

        <div className="flex flex-wrap gap-1.5">
          {(['all', ...SEVERITY_ORDER] as SeverityFilter[]).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setSeverity(option)}
              className={cn(
                'rounded-lg border px-3 py-1.5 text-[12px] font-medium capitalize transition-colors',
                severity === option
                  ? 'border-brand/40 bg-brand/12 text-ink'
                  : 'border-line bg-surface text-muted hover:text-ink',
              )}
            >
              {option === 'all' ? 'All' : SEVERITY[option].label}
            </button>
          ))}
        </div>

        <p className="text-faint ml-auto text-[12px] tabular-nums">
          {filtered.length} of {governanceAssets.length} assets
        </p>
      </div>

      {/* Table. */}
      <Card className="overflow-x-auto p-0">
        {filtered.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="No assets match"
            description="Try clearing the search or widening the severity filter."
          />
        ) : (
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead>
              <tr className="border-line text-faint border-b text-[11px] font-semibold tracking-widest uppercase">
                <th className="px-4 py-3">Asset</th>
                <th className="px-4 py-3">Owner</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">Coverage</th>
                <th className="px-4 py-3">Documentation</th>
                <th className="px-4 py-3">Health</th>
                <th className="px-4 py-3">Updated</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((asset) => (
                <AssetRow key={asset.urn} asset={asset} />
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}

function AssetRow({ asset }: { asset: GovernanceAsset }) {
  return (
    <tr className="border-line hover:bg-raised/50 border-b transition-colors last:border-0">
      <td className="px-4 py-3">
        <p className="text-ink text-[13px] font-semibold">{asset.name}</p>
        <p className="text-faint mt-0.5 text-[11.5px]">
          {asset.platform} · {asset.domain}
        </p>
      </td>
      <td className="px-4 py-3">
        {asset.owner ? (
          <span className="border-line bg-raised text-ink-secondary inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11.5px] font-medium">
            <span className="from-brand to-accent grid size-4 place-items-center rounded-full bg-gradient-to-br text-[8px] font-bold text-white">
              {asset.owner.slice(0, 1).toUpperCase()}
            </span>
            {asset.owner}
          </span>
        ) : (
          <span className="border-critical/25 bg-critical/10 text-critical inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11.5px] font-medium">
            <UserX className="size-3" /> Unowned
          </span>
        )}
      </td>
      <td className="px-4 py-3">
        <StatusBadge severity={asset.severity} />
      </td>
      <td className="px-4 py-3">
        <MeterCell value={asset.coverage} />
      </td>
      <td className="px-4 py-3">
        <MeterCell value={asset.documentation} />
      </td>
      <td className="px-4 py-3">
        <MeterCell value={asset.health} emphasize />
      </td>
      <td className="text-muted px-4 py-3 text-[12px] whitespace-nowrap">
        {timeAgo(asset.lastModified)}
      </td>
    </tr>
  )
}

/** Percentage with a severity-tinted micro bar — reads faster than digits. */
function MeterCell({ value, emphasize }: { value: number; emphasize?: boolean }) {
  const tone =
    value < 40 ? 'bg-critical' : value < 60 ? 'bg-warning' : value < 80 ? 'bg-brand' : 'bg-positive'

  return (
    <div className="flex min-w-[90px] items-center gap-2.5">
      <div className="bg-line h-1.5 w-14 overflow-hidden rounded-full">
        <div className={cn('h-full rounded-full', tone)} style={{ width: `${value}%` }} />
      </div>
      <span
        className={cn(
          'text-[12px] tabular-nums',
          emphasize ? 'text-ink font-semibold' : 'text-muted',
        )}
      >
        {value}%
      </span>
    </div>
  )
}
