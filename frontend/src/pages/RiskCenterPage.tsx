import { ArrowRight, ShieldCheck, UserX } from 'lucide-react'
import { useNavigate } from 'react-router'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  Card,
  IssueCard,
  LoadingSkeleton,
  PageHeader,
  RiskBadge,
  SectionHeader,
  SourceTag,
  Timeline,
  type TimelineItem,
} from '@/components/ui'
import { useCountUp } from '@/hooks/useCountUp'
import { useRiskOverview, useRiskTrend, useViolations } from '@/hooks/queries'
import type { Severity } from '@/types/domain'
import { cn } from '@/utils'
import { SEVERITY, SEVERITY_ORDER } from '@/utils/severity'

export function RiskCenterPage() {
  const navigate = useNavigate()
  const overview = useRiskOverview()
  const trend = useRiskTrend()
  const violations = useViolations()

  const counts = overview.data?.data.counts
  const topAssets = overview.data?.data.topAssets ?? []

  const timeline: TimelineItem[] = (violations.data?.data ?? []).map((finding) => ({
    id: finding.id,
    timestamp: finding.detectedAt,
    title: finding.title,
    description: finding.summary,
    severity: finding.severity,
  }))

  return (
    <div>
      <PageHeader
        title="Risk Center"
        description="Where governance risk is concentrated, and whether it is moving the right way."
        action={
          overview.data ? (
            <SourceTag source={overview.data.source} reason={overview.data.reason} />
          ) : null
        }
      />

      {/* Severity distribution. */}
      {overview.isPending || !counts ? (
        <LoadingSkeleton variant="metric" count={4} />
      ) : (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          {SEVERITY_ORDER.map((severity) => (
            <SeverityCard
              key={severity}
              severity={severity}
              count={counts[severity]}
              total={overview.data?.data.totalAssets ?? 0}
            />
          ))}
        </div>
      )}

      {/* Trend. */}
      <Card className="mt-6 p-5">
        <SectionHeader
          title="Risk Distribution Over Time"
          description="Open findings by severity across the last two weeks."
          action={
            trend.data ? (
              <SourceTag source={trend.data.source} reason={trend.data.reason} />
            ) : null
          }
        />
        {trend.isPending ? (
          <LoadingSkeleton variant="chart" />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={trend.data?.data ?? []}
                margin={{ top: 4, right: 8, bottom: 0, left: -18 }}
              >
                <defs>
                  {SEVERITY_ORDER.map((severity) => (
                    <linearGradient
                      key={severity}
                      id={`risk-grad-${severity}`}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor={SEVERITY[severity].hex}
                        stopOpacity={0.28}
                      />
                      <stop
                        offset="100%"
                        stopColor={SEVERITY[severity].hex}
                        stopOpacity={0}
                      />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid stroke="var(--t-line)" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="var(--t-faint)"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  dy={6}
                />
                <YAxis
                  stroke="var(--t-faint)"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  cursor={{ stroke: 'var(--t-line-strong)' }}
                  contentStyle={{
                    background: 'var(--t-raised)',
                    border: '1px solid var(--t-line)',
                    borderRadius: 10,
                    fontSize: 12,
                    color: 'var(--t-ink)',
                    boxShadow: 'var(--t-shadow)',
                  }}
                  labelStyle={{ color: 'var(--t-muted)', marginBottom: 4 }}
                />
                {/* Drawn low→critical so critical sits visually on top. */}
                {[...SEVERITY_ORDER].reverse().map((severity) => (
                  <Area
                    key={severity}
                    type="monotone"
                    dataKey={severity}
                    name={SEVERITY[severity].label}
                    stroke={SEVERITY[severity].hex}
                    strokeWidth={1.75}
                    fill={`url(#risk-grad-${severity})`}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {/* Top risk assets. */}
        <div>
          <SectionHeader
            title="Top Risk Assets"
            description="Lowest composite health — fix these first."
            action={
              <button
                type="button"
                onClick={() => navigate('/governance')}
                className="text-brand-strong flex items-center gap-1 text-[12.5px] font-medium hover:underline"
              >
                Open Governance <ArrowRight className="size-3.5" />
              </button>
            }
          />
          {overview.isPending ? (
            <LoadingSkeleton variant="card" count={4} />
          ) : topAssets.length === 0 ? (
            <Card className="p-6 text-center">
              <ShieldCheck className="text-positive mx-auto size-7" strokeWidth={1.75} />
              <p className="text-ink mt-2.5 text-sm font-semibold">No assets at risk</p>
            </Card>
          ) : (
            <div className="space-y-2.5">
              {topAssets.map((asset, index) => (
                <Card
                  key={asset.urn}
                  interactive
                  onClick={() =>
                    navigate('/investigator', {
                      state: { prompt: `Why is ${asset.name} risky?` },
                    })
                  }
                  className="flex items-center gap-4 px-4 py-3"
                >
                  <span className="text-faint w-5 text-center font-mono text-[12px] tabular-nums">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-ink truncate text-[13px] font-semibold">
                      {asset.name}
                    </p>
                    <p className="text-faint text-[11.5px]">
                      {asset.platform} · {asset.domain}
                    </p>
                  </div>
                  {!asset.owner ? (
                    <span className="text-critical hidden items-center gap-1 text-[11.5px] font-medium sm:flex">
                      <UserX className="size-3.5" /> Unowned
                    </span>
                  ) : null}
                  <RiskBadge severity={asset.severity} score={asset.health} size="sm" />
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Violations timeline. */}
        <div>
          <SectionHeader
            title="Governance Violations"
            description="Findings in the order they were detected."
            action={
              violations.data ? (
                <SourceTag
                  source={violations.data.source}
                  reason={violations.data.reason}
                />
              ) : null
            }
          />
          <Card className="p-5">
            {violations.isPending ? (
              <LoadingSkeleton count={5} />
            ) : timeline.length > 0 ? (
              <Timeline items={timeline} />
            ) : (
              <div className="py-8 text-center">
                <ShieldCheck className="text-positive mx-auto size-7" strokeWidth={1.75} />
                <p className="text-ink mt-2.5 text-sm font-semibold">No violations</p>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Critical issues, expanded. */}
      {(violations.data?.data ?? []).some((f) => f.severity === 'critical') ? (
        <div className="mt-8">
          <SectionHeader
            title="Critical Issues"
            description="Requiring attention before anything else."
          />
          <div className="grid gap-3 md:grid-cols-2">
            {(violations.data?.data ?? [])
              .filter((finding) => finding.severity === 'critical')
              .map((finding) => (
                <IssueCard
                  key={finding.id}
                  finding={finding}
                  onAction={(action) =>
                    navigate('/investigator', {
                      state: { prompt: `${action} for ${finding.assetName}` },
                    })
                  }
                />
              ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function SeverityCard({
  severity,
  count,
  total,
}: {
  severity: Severity
  count: number
  total: number
}) {
  const style = SEVERITY[severity]
  const animated = useCountUp(count)
  const share = total > 0 ? Math.round((count / total) * 100) : 0

  return (
    <Card className={cn('border p-5', style.bg)}>
      <div className="flex items-center justify-between">
        <p className={cn('text-[12px] font-semibold tracking-widest uppercase', style.text)}>
          {style.label}
        </p>
        <span className={cn('size-2 rounded-full', style.dot)} />
      </div>
      <p className="text-ink mt-3 text-3xl font-semibold tracking-tight tabular-nums">
        {Math.round(animated)}
      </p>
      <p className="text-muted mt-1 text-[12px]">
        {share}% of {total} assets
      </p>
    </Card>
  )
}
