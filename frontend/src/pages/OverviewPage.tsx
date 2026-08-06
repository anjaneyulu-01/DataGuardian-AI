import {
  Activity,
  Boxes,
  Database,
  FileText,
  GitBranch,
  ShieldCheck,
  TriangleAlert,
  UserX,
  Users,
} from 'lucide-react'
import { useNavigate } from 'react-router'

import {
  ActivityFeed,
  Card,
  HealthScore,
  IssueCard,
  LoadingSkeleton,
  MetricCard,
  ScanBrief,
  SectionHeader,
  SourceTag,
} from '@/components/ui'
import { useActivity, useOverview, useViolations } from '@/hooks/queries'
import { formatNumber } from '@/utils/format'

export function OverviewPage() {
  const navigate = useNavigate()
  const overview = useOverview()
  const activity = useActivity()
  const violations = useViolations()

  const askInvestigator = (prompt: string) => {
    navigate('/investigator', { state: { prompt } })
  }

  const metrics = overview.data?.data
  const criticalFindings = (violations.data?.data ?? []).filter(
    (finding) => finding.severity === 'critical',
  )

  return (
    <div>
      {/* The brief leads. A steward opening this page needs the conclusion
          first; the supporting counts are below it, not in place of it. */}
      {overview.isPending || !metrics ? (
        <LoadingSkeleton variant="card" count={1} />
      ) : (
        <ScanBrief
          metrics={metrics}
          source={overview.data?.source ?? 'demo'}
          reason={overview.data?.reason}
          readAt={overview.dataUpdatedAt || null}
          onAsk={askInvestigator}
        />
      )}

      {/* Supporting counts. No deltas: without persisted scan history there
          is no previous value to compare against, and an estimated one reads
          as measured no matter how it is labelled. */}
      {overview.isPending || !metrics ? (
        <LoadingSkeleton variant="metric" count={5} className="mt-6" />
      ) : (
        <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          <MetricCard
            label="Metadata Health"
            value={metrics.score}
            suffix="/100"
            icon={Activity}
          />
          <MetricCard
            label="Critical Issues"
            value={metrics.criticalIssues}
            icon={TriangleAlert}
            tone="critical"
          />
          <MetricCard
            label="Datasets"
            value={metrics.totalAssets}
            icon={Database}
            tone="positive"
          />
          <MetricCard label="Owners" value={metrics.owners} icon={Users} />
          <MetricCard label="Domains" value={metrics.domainCount} icon={Boxes} />
          <MetricCard
            label="Missing Owners"
            value={metrics.missingOwners}
            icon={UserX}
            tone="critical"
          />
          <MetricCard
            label="Lineage Coverage"
            value={metrics.lineageCoverage}
            suffix="%"
            icon={GitBranch}
          />
          <MetricCard
            label="Documentation"
            value={metrics.documentationCoverage}
            suffix="%"
            icon={FileText}
          />
        </div>
      )}

      {/* Score + critical findings. */}
      <div className="mt-6 grid gap-4 lg:grid-cols-[320px_1fr]">
        <Card className="flex flex-col items-center justify-center gap-2 p-6">
          {metrics ? (
            <>
              <HealthScore score={metrics.score} />
              <p className="text-muted max-w-55 text-center text-[12.5px] leading-relaxed">
                Composite of ownership, documentation, and classification across{' '}
                {formatNumber(metrics.totalAssets)} assets.
              </p>
            </>
          ) : (
            <LoadingSkeleton count={3} className="w-full" />
          )}
        </Card>

        <div>
          <SectionHeader
            title="Recent AI Findings"
            description="Highest-impact issues from the latest analysis."
            action={
              violations.data ? (
                <SourceTag
                  source={violations.data.source}
                  reason={violations.data.reason}
                />
              ) : null
            }
          />
          {violations.isPending ? (
            <LoadingSkeleton variant="card" count={2} />
          ) : criticalFindings.length > 0 ? (
            <div className="space-y-3">
              {criticalFindings.map((finding) => (
                <IssueCard
                  key={finding.id}
                  finding={finding}
                  onAction={(action) =>
                    askInvestigator(`${action} for ${finding.assetName}`)
                  }
                />
              ))}
            </div>
          ) : (
            <Card className="p-6 text-center">
              <ShieldCheck className="text-positive mx-auto size-7" strokeWidth={1.75} />
              <p className="text-ink mt-2.5 text-sm font-semibold">
                No critical findings
              </p>
              <p className="text-muted mt-1 text-[12.5px]">
                Ask the AI Investigator to run a fresh analysis.
              </p>
            </Card>
          )}
        </div>
      </div>

      {/* Agent activity. */}
      <div className="mt-8">
        <Card className="p-5">
          <SectionHeader
            title="Recent Agent Activity"
            description="Scans, fixes, and documentation runs."
            action={
              activity.data ? (
                <SourceTag source={activity.data.source} reason={activity.data.reason} />
              ) : null
            }
          />
          {activity.isPending ? (
            <LoadingSkeleton count={4} />
          ) : (
            <ActivityFeed events={activity.data?.data ?? []} />
          )}
        </Card>
      </div>
    </div>
  )
}
