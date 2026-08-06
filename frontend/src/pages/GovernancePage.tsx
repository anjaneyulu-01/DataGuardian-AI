import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  GitBranch,
  ShieldCheck,
  UserX,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'

import {
  Card,
  EmptyState,
  FilterBar,
  LoadingSkeleton,
  PageHeader,
  RiskBadge,
  SearchBar,
  SourceTag,
  type FilterOption,
} from '@/components/ui'
import { useGovernanceAssets } from '@/hooks/queries'
import type { GovernanceAsset, Severity } from '@/types/domain'
import { cn } from '@/utils'
import { timeAgo } from '@/utils/format'
import { SEVERITY, SEVERITY_ORDER } from '@/utils/severity'

type SeverityFilter = Severity | 'all'
type SortKey =
  | 'name'
  | 'owner'
  | 'health'
  | 'documentation'
  | 'coverage'
  | 'severity'
  | 'downstreamCount'
type SortDirection = 'asc' | 'desc'

const PAGE_SIZE = 15

/** Stable empty array, so a pending query does not invalidate the memos. */
const EMPTY_ASSETS: GovernanceAsset[] = []

/** Rank used when sorting by risk, so critical sorts as "worst". */
const SEVERITY_RANK: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

export function GovernancePage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState<SeverityFilter>('all')
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'health',
    direction: 'asc', // worst first — the order a steward works through
  })
  const [page, setPage] = useState(0)

  // Server-side search; the backend re-queries DataHub on each committed term.
  const query = useGovernanceAssets({ search, count: 100 })
  // `?? EMPTY` rather than `?? []`: a fresh array literal each render would
  // change identity and defeat the memos below.
  const assets = query.data?.data.assets ?? EMPTY_ASSETS

  const counts = useMemo(() => {
    const tally: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0 }
    for (const asset of assets) tally[asset.severity] += 1
    return tally
  }, [assets])

  const filtered = useMemo(() => {
    const subset =
      severity === 'all' ? assets : assets.filter((a) => a.severity === severity)

    const direction = sort.direction === 'asc' ? 1 : -1
    return [...subset].sort((a, b) => compare(a, b, sort.key) * direction)
  }, [assets, severity, sort])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  // Clamp rather than reset: a filter change that shrinks the list should
  // land on the last page, not silently jump to the first.
  const safePage = Math.min(page, pageCount - 1)
  const visible = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE)

  const filterOptions: FilterOption<SeverityFilter>[] = [
    { value: 'all', label: 'All', count: assets.length },
    ...SEVERITY_ORDER.map((level) => ({
      value: level as SeverityFilter,
      label: SEVERITY[level].label,
      count: counts[level],
    })),
  ]

  const toggleSort = (key: SortKey) => {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
        : { key, direction: key === 'name' || key === 'owner' ? 'asc' : 'asc' },
    )
    setPage(0)
  }

  return (
    <div>
      <PageHeader
        title="Governance"
        description="Every catalogued asset scored on coverage, documentation, and health."
        action={
          query.data ? (
            <SourceTag source={query.data.source} reason={query.data.reason} />
          ) : null
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchBar
          value={search}
          onChange={(value) => {
            setSearch(value)
            setPage(0)
          }}
          placeholder="Search assets, owners, domains…"
          className="min-w-56 flex-1 sm:max-w-xs"
        />
        <FilterBar
          options={filterOptions}
          value={severity}
          onChange={(value) => {
            setSeverity(value)
            setPage(0)
          }}
          onClear={() => setSeverity('all')}
        />
        <p className="text-faint ml-auto text-[12px] tabular-nums">
          {filtered.length} of {query.data?.data.total ?? assets.length}
        </p>
      </div>

      {query.isPending ? (
        <LoadingSkeleton variant="table" count={8} />
      ) : filtered.length === 0 ? (
        <Card className="p-0">
          <EmptyState
            icon={ShieldCheck}
            title={search ? 'No assets match your search' : 'No assets found'}
            description={
              search
                ? 'Try a different term, or clear the severity filter.'
                : 'DataHub returned no datasets. Check the connection in Settings.'
            }
          />
        </Card>
      ) : (
        <>
          <Card className="overflow-x-auto p-0">
            <table className="w-full min-w-[1040px] border-collapse text-left">
              <thead>
                <tr className="border-line text-faint border-b text-[11px] font-semibold tracking-widest uppercase">
                  <SortableHeader
                    label="Dataset"
                    sortKey="name"
                    sort={sort}
                    onSort={toggleSort}
                  />
                  <SortableHeader
                    label="Owner"
                    sortKey="owner"
                    sort={sort}
                    onSort={toggleSort}
                  />
                  <SortableHeader
                    label="Health"
                    sortKey="health"
                    sort={sort}
                    onSort={toggleSort}
                  />
                  <SortableHeader
                    label="Documentation"
                    sortKey="documentation"
                    sort={sort}
                    onSort={toggleSort}
                  />
                  <SortableHeader
                    label="Coverage"
                    sortKey="coverage"
                    sort={sort}
                    onSort={toggleSort}
                  />
                  <SortableHeader
                    label="Risk"
                    sortKey="severity"
                    sort={sort}
                    onSort={toggleSort}
                  />
                  <SortableHeader
                    label="Lineage"
                    sortKey="downstreamCount"
                    sort={sort}
                    onSort={toggleSort}
                  />
                  <th className="px-4 py-3">Tags</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((asset) => (
                  <AssetRow
                    key={asset.urn}
                    asset={asset}
                    onInspect={() =>
                      navigate('/investigator', {
                        state: { prompt: `Why is ${asset.name} risky?` },
                      })
                    }
                  />
                ))}
              </tbody>
            </table>
          </Card>

          {pageCount > 1 ? (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-faint text-[12px] tabular-nums">
                Page {safePage + 1} of {pageCount}
              </p>
              <div className="flex gap-2">
                <PageButton
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={safePage === 0}
                  label="Previous page"
                >
                  <ChevronLeft className="size-4" />
                </PageButton>
                <PageButton
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  disabled={safePage >= pageCount - 1}
                  label="Next page"
                >
                  <ChevronRight className="size-4" />
                </PageButton>
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}

function compare(a: GovernanceAsset, b: GovernanceAsset, key: SortKey): number {
  switch (key) {
    case 'name':
      return a.name.localeCompare(b.name)
    case 'owner':
      // Unowned assets sort first — they are the ones needing attention.
      return (a.owner ?? '').localeCompare(b.owner ?? '')
    case 'severity':
      return SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]
    default:
      return a[key] - b[key]
  }
}

function SortableHeader({
  label,
  sortKey,
  sort,
  onSort,
}: {
  label: string
  sortKey: SortKey
  sort: { key: SortKey; direction: SortDirection }
  onSort: (key: SortKey) => void
}) {
  const isActive = sort.key === sortKey
  return (
    <th className="px-4 py-3">
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        aria-sort={isActive ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}
        className={cn(
          'inline-flex items-center gap-1 tracking-widest uppercase transition-colors',
          isActive ? 'text-ink-secondary' : 'hover:text-muted',
        )}
      >
        {label}
        {isActive ? (
          sort.direction === 'asc' ? (
            <ArrowUp className="size-3" />
          ) : (
            <ArrowDown className="size-3" />
          )
        ) : null}
      </button>
    </th>
  )
}

function AssetRow({
  asset,
  onInspect,
}: {
  asset: GovernanceAsset
  onInspect: () => void
}) {
  return (
    <tr
      onClick={onInspect}
      className="border-line hover:bg-raised/50 cursor-pointer border-b transition-colors last:border-0"
    >
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
        <Meter value={asset.health} emphasize />
      </td>
      <td className="px-4 py-3">
        <Meter value={asset.documentation} />
      </td>
      <td className="px-4 py-3">
        <Meter value={asset.coverage} />
      </td>
      <td className="px-4 py-3">
        <RiskBadge severity={asset.severity} size="sm" />
      </td>
      <td className="px-4 py-3">
        {asset.downstreamCount > 0 ? (
          <span className="text-ink-secondary inline-flex items-center gap-1 text-[12px] tabular-nums">
            <GitBranch className="text-faint size-3" />
            {asset.downstreamCount}
          </span>
        ) : (
          <span className="text-faint text-[12px]">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        {asset.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {asset.tags.slice(0, 2).map((tag) => (
              <span
                key={tag}
                className="border-line bg-raised text-muted rounded-full border px-1.5 py-0.5 text-[10.5px] font-medium"
              >
                {tag}
              </span>
            ))}
            {asset.tags.length > 2 ? (
              <span
                className="text-faint text-[10.5px]"
                title={asset.tags.slice(2).join(', ')}
              >
                +{asset.tags.length - 2}
              </span>
            ) : null}
          </div>
        ) : (
          <span className="text-faint text-[12px]">—</span>
        )}
      </td>
      <td className="text-muted px-4 py-3 text-[12px] whitespace-nowrap">
        {asset.tags.some((tag) => tag.toLowerCase().includes('deprecated')) ? (
          <span className="text-warning font-medium">Deprecated</span>
        ) : (
          timeAgo(asset.lastModified)
        )}
      </td>
    </tr>
  )
}

/** Percentage with a severity-tinted micro bar — reads faster than digits. */
function Meter({ value, emphasize }: { value: number; emphasize?: boolean }) {
  const tone =
    value < 40
      ? 'bg-critical'
      : value < 60
        ? 'bg-warning'
        : value < 80
          ? 'bg-brand'
          : 'bg-positive'

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

function PageButton({
  onClick,
  disabled,
  label,
  children,
}: {
  onClick: () => void
  disabled: boolean
  label: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="border-line bg-surface text-muted hover:text-ink grid size-8 place-items-center rounded-lg border transition-colors disabled:opacity-40"
    >
      {children}
    </button>
  )
}
