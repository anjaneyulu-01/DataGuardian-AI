import {
  Activity,
  BarChart3,
  BookText,
  Boxes,
  Database,
  FileText,
  GitBranch,
  ShieldCheck,
  TriangleAlert,
  UserX,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useNavigate } from 'react-router'

import {
  ActivityFeed,
  Card,
  HealthScore,
  IssueCard,
  LoadingSkeleton,
  MetricCard,
  PageHeader,
  SectionHeader,
  SourceTag,
} from '@/components/ui'
import { useActivity, useOverview, useViolations } from '@/hooks/queries'
import { formatNumber } from '@/utils/format'

/** Quick actions route into the Investigator with the prompt pre-fired. */
const QUICK_ACTIONS: { label: string; icon: LucideIcon; prompt: string }[] = [
  {
    label: 'Analyze Governance',
    icon: BarChart3,
    prompt: 'Analyze governance health across the catalogue',
  },
  {
    label: 'Generate Governance Report',
    icon: FileText,
    prompt: 'Create a governance report',
  },
  {
    label: 'Find High Risk Assets',
    icon: TriangleAlert,
    prompt: 'Which datasets are highest risk?',
  },
  {
    label: 'Generate Documentation',
    icon: BookText,
    prompt: 'Generate documentation for the least documented dataset',
  },
]

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
      <PageHeader
        title="Governance posture"
        description={
          metrics
            ? `${formatNumber(metrics.totalAssets)} assets under watch in the connected DataHub instance.`
            : 'Reading your catalogue…'
        }
        action={
          overview.data ? (
            <SourceTag source={overview.data.source} reason={overview.data.reason} />
          ) : null
        }
      />

      {/* KPI row. */}
      {overview.isPending || !metrics ? (
        <LoadingSkeleton variant="metric" count={5} />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
          <MetricCard
            label="Metadata Health"
            value={metrics.score}
            suffix="/100"
            icon={Activity}
            delta={metrics.deltas.score}
          />
          <MetricCard
            label="Critical Issues"
            value={metrics.criticalIssues}
            icon={TriangleAlert}
            delta={metrics.deltas.criticalIssues}
            deltaInverted
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
            delta={metrics.deltas.coverage}
          />
        </div>
      )}

      {/* Score + critical findings. */}
      <div className="mt-6 grid gap-4 lg:grid-cols-[320px_1fr]">
        <Card className="flex flex-col items-center justify-center gap-2 p-6">
          {metrics ? (
            <>
              <HealthScore score={metrics.score} />
              <p className="text-muted max-w-[220px] text-center text-[12.5px] leading-relaxed">
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

      {/* Quick actions. */}
      <div className="mt-8">
        <SectionHeader
          title="Quick Actions"
          description="One click starts a full agent investigation."
        />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {QUICK_ACTIONS.map(({ label, icon: Icon, prompt }) => (
            <Card
              key={label}
              interactive
              onClick={() => askInvestigator(prompt)}
              className="group flex flex-col gap-3 p-4"
            >
              <span className="border-brand/25 bg-brand/10 text-brand-strong group-hover:shadow-glow grid size-9 place-items-center rounded-lg border transition-shadow">
                <Icon className="size-4.5" strokeWidth={2} />
              </span>
              <p className="text-ink text-[13px] leading-snug font-semibold">{label}</p>
            </Card>
          ))}
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
