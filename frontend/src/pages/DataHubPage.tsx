import {
  Boxes,
  Braces,
  Database,
  Gauge,
  Link2,
  Server,
  Timer,
  Users,
  Zap,
} from 'lucide-react'

import {
  Card,
  LoadingSkeleton,
  PageHeader,
  SectionHeader,
  SourceTag,
  StatusIndicator,
} from '@/components/ui'
import { useDataHubReport } from '@/hooks/queries'
import { GRAPHQL_DOCUMENTS, fetchLastSync } from '@/services/datahubService'
import type { CoverageMetric, EntityBreakdown } from '@/services/datahubService'
import { cn } from '@/utils'
import { formatNumber } from '@/utils/format'

/**
 * The DataHub integration, evidenced rather than asserted.
 *
 * The rest of the product consumes DataHub metadata; this page proves it, by
 * showing the connection, the queries the integration issues, what came back,
 * and the cache behaviour in front of it.
 *
 * The rule throughout: a figure the API could not supply renders as
 * "not available", never as zero. Zero means "we measured none"; that
 * distinction is the entire credibility of the page.
 */
export function DataHubPage() {
  const report = useDataHubReport()
  const lastSync = fetchLastSync()

  const data = report.data?.data
  const health = data?.health

  return (
    <div>
      <PageHeader
        title="DataHub integration"
        description="The connection, the queries, and what the catalogue returned."
        action={
          report.data ? (
            <SourceTag source={report.data.source} reason={report.data.reason} />
          ) : null
        }
      />

      {report.isPending || !data ? (
        <LoadingSkeleton variant="metric" count={4} />
      ) : (
        <>
          {/* Connection. */}
          <Card className="p-5">
            <div className="flex flex-wrap items-center gap-3">
              <StatusIndicator
                state={health?.reachable ? 'online' : 'offline'}
                label={health?.reachable ? 'Connected' : 'Not connected'}
              />
              <code className="text-muted bg-raised rounded-md px-2 py-1 font-mono text-[11.5px]">
                {health?.gms_url}
              </code>
              {health?.version ? (
                <span className="border-brand/30 bg-brand/10 text-brand-strong rounded-md border px-2 py-1 text-[11px] font-medium">
                  GMS {health.version}
                </span>
              ) : null}
              {health?.latency_ms != null ? (
                <span className="text-muted inline-flex items-center gap-1.5 text-[11.5px] tabular-nums">
                  <Timer className="size-3.5" />
                  {Math.round(health.latency_ms)}ms
                </span>
              ) : null}
              <span className="text-faint ml-auto text-[11.5px]">
                {health?.authenticated ? 'Token authenticated' : 'Unauthenticated'}
              </span>
            </div>

            {health?.error ? (
              <p className="text-warning mt-2.5 text-[12px] leading-relaxed">
                {health.error}
              </p>
            ) : null}
          </Card>

          {/* Entity counts. */}
          <div className="mt-4">
            <SectionHeader
              title="Catalogue contents"
              description={
                data.totalAssets != null
                  ? `${formatNumber(data.totalAssets)} datasets reported; coverage computed over a ${data.sampleSize}-asset sample.`
                  : 'Entity counts as reported by DataHub.'
              }
            />
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {data.entities.map((entity) => (
                <EntityCard key={entity.label} entity={entity} />
              ))}
            </div>
          </div>

          {/* Metadata coverage. */}
          <div className="mt-6">
            <SectionHeader
              title="Metadata coverage"
              description={`Measured across ${data.sampleSize} assets returned by DataHub — these are the inputs the risk engine scores.`}
            />
            <Card className="divide-line divide-y p-0">
              {data.coverage.map((metric) => (
                <CoverageRow key={metric.label} metric={metric} />
              ))}
            </Card>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            {/* Cache. */}
            <div>
              <SectionHeader
                title="Query cache"
                description="TTL + LRU with single-flight, in front of every GMS read."
              />
              <Card className="p-5">
                {data.cache ? (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <Stat
                        icon={<Zap className="size-3.5" />}
                        label="Hit rate"
                        value={`${Math.round(data.cache.hit_rate * 100)}%`}
                      />
                      <Stat
                        icon={<Gauge className="size-3.5" />}
                        label="Entries"
                        value={formatNumber(data.cache.entries)}
                      />
                      <Stat
                        icon={<Zap className="size-3.5" />}
                        label="Hits"
                        value={formatNumber(data.cache.hits)}
                      />
                      <Stat
                        icon={<Server className="size-3.5" />}
                        label="Misses"
                        value={formatNumber(data.cache.misses)}
                      />
                    </div>
                    <p className="text-muted mt-3 text-[11.5px] leading-relaxed">
                      Counters are per-process and reset on restart. Failures are
                      never cached, so a DataHub blip cannot be pinned in place
                      for the whole TTL.
                    </p>
                  </>
                ) : (
                  <p className="text-muted text-[12.5px] leading-relaxed">
                    Cache statistics are not available — they are reported by the
                    live backend only.
                  </p>
                )}
              </Card>
            </div>

            {/* Platforms. */}
            <div>
              <SectionHeader
                title="Source platforms"
                description="Systems the sampled assets originate from."
              />
              <Card className="p-5">
                {data.platforms.length > 0 ? (
                  <ul className="space-y-2">
                    {data.platforms.map((platform) => (
                      <li
                        key={platform.name}
                        className="flex items-center justify-between gap-3"
                      >
                        <span className="text-ink inline-flex items-center gap-2 text-[12.5px] font-medium">
                          <Database className="text-faint size-3.5" />
                          {platform.name}
                        </span>
                        <span className="text-muted text-[12px] tabular-nums">
                          {platform.count}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted text-[12.5px]">
                    No platform information in the sample.
                  </p>
                )}
              </Card>
            </div>
          </div>

          {/* GraphQL documents. */}
          <div className="mt-6">
            <SectionHeader
              title="GraphQL documents"
              description="Every query the integration can issue. All 12 are validated against a live DataHub v1.5.0.6 by an acceptance harness in CI."
            />
            <Card className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[520px] text-left">
                  <thead>
                    <tr className="border-line bg-raised/50 border-b">
                      <Th>Document</Th>
                      <Th>Entity</Th>
                      <Th>Purpose</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-line divide-y">
                    {GRAPHQL_DOCUMENTS.map((doc) => (
                      <tr key={doc.name}>
                        <td className="px-4 py-2.5">
                          <code className="text-brand-strong inline-flex items-center gap-1.5 font-mono text-[11.5px]">
                            <Braces className="size-3" />
                            {doc.name}
                          </code>
                        </td>
                        <td className="text-muted px-4 py-2.5 text-[12px]">
                          {doc.entity}
                        </td>
                        <td className="text-ink-secondary px-4 py-2.5 text-[12px]">
                          {doc.purpose}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Sync — honestly absent. */}
          <div className="mt-6">
            <SectionHeader
              title="Ingestion"
              action={<SourceTag source="demo" reason={lastSync.reason} />}
            />
            <Card className="p-5">
              <p className="text-ink-secondary text-[12.5px] leading-relaxed">
                <Link2 className="text-faint mr-1.5 inline size-3.5" />
                DataGuardian is a <strong>read-only consumer</strong> of DataHub.
                It issues no mutations and runs no ingestion of its own, so
                there is no last-sync timestamp to report — metadata is read on
                demand and cached for {60} seconds.
              </p>
              <p className="text-muted mt-2 text-[11.5px] leading-relaxed">
                Ingestion cadence is a property of your DataHub deployment.
                Reporting a sync time here would imply a pipeline this product
                does not run.
              </p>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

function EntityCard({ entity }: { entity: EntityBreakdown }) {
  const ICONS: Record<string, typeof Database> = {
    Datasets: Database,
    Owners: Users,
    Domains: Boxes,
    Platforms: Server,
  }
  const Icon = ICONS[entity.label] ?? Database

  return (
    <Card className="p-4">
      <span className="text-faint flex items-center gap-1.5">
        <Icon className="size-3.5" />
        <span className="text-[11px] font-semibold tracking-wide uppercase">
          {entity.label}
        </span>
      </span>
      {entity.count != null ? (
        <p className="text-ink mt-1.5 text-2xl font-semibold tabular-nums">
          {formatNumber(entity.count)}
        </p>
      ) : (
        <p className="text-faint mt-1.5 text-[13px] font-medium">Not available</p>
      )}
      <p className="text-muted mt-1 text-[11.5px] leading-snug">{entity.detail}</p>
    </Card>
  )
}

function CoverageRow({ metric }: { metric: CoverageMetric }) {
  const percent = metric.percent

  return (
    <div className="px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="text-ink text-[12.5px] font-medium">{metric.label}</span>
        <span className="text-muted text-[11.5px]">{metric.detail}</span>
        <span className="text-ink ml-auto text-[13px] font-semibold tabular-nums">
          {percent != null ? `${percent}%` : 'Not available'}
        </span>
      </div>
      {percent != null ? (
        <>
          <div className="bg-raised mt-2 h-1.5 overflow-hidden rounded-full">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                percent >= 80
                  ? 'bg-positive'
                  : percent >= 50
                    ? 'bg-warning'
                    : 'bg-critical',
              )}
              style={{ width: `${percent}%` }}
            />
          </div>
          <p className="text-faint mt-1 text-[11px] tabular-nums">
            {metric.covered} of {metric.total} assets
          </p>
        </>
      ) : null}
    </div>
  )
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="border-line bg-raised/40 rounded-lg border px-3 py-2.5">
      <span className="text-faint flex items-center gap-1.5 text-[10.5px] font-semibold tracking-wide uppercase">
        {icon}
        {label}
      </span>
      <p className="text-ink mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-faint px-4 py-2.5 text-[10.5px] font-semibold tracking-widest uppercase">
      {children}
    </th>
  )
}
