import {
  Activity,
  BarChart3,
  FileText,
  GitBranch,
  Search,
  ShieldCheck,
  TriangleAlert,
  Users,
  Waypoints,
  type LucideIcon,
} from 'lucide-react'
import { useNavigate } from 'react-router'

import {
  ActivityFeed,
  Card,
  HealthScore,
  MetricCard,
  PageHeader,
  RiskCard,
  SectionHeader,
  Timeline,
  type TimelineItem,
} from '@/components/ui'
import { activityFeed, findings, healthSummary } from '@/data/mockData'
import { formatNumber } from '@/utils/format'

/** Quick AI actions route into the Investigator with the prompt pre-fired. */
const QUICK_ACTIONS: { label: string; icon: LucideIcon; prompt: string }[] = [
  { label: 'Analyze Governance', icon: BarChart3, prompt: 'Analyze metadata health across the catalogue' },
  { label: 'Find High Risk Assets', icon: TriangleAlert, prompt: 'Which assets are highest risk?' },
  { label: 'Generate Documentation', icon: FileText, prompt: 'Generate documentation for dim_customer' },
  { label: 'Show Downstream Impact', icon: Waypoints, prompt: 'Explain downstream impact of fct_payments' },
  { label: 'Create Governance Report', icon: Search, prompt: 'Create a governance report' },
]

export function OverviewPage() {
  const navigate = useNavigate()
  const summary = healthSummary
  const critical = findings.filter((f) => f.severity === 'critical')

  const recentFindings: TimelineItem[] = findings.map((finding) => ({
    id: finding.id,
    timestamp: finding.detectedAt,
    title: finding.title,
    description: finding.summary,
    severity: finding.severity,
  }))

  const askInvestigator = (prompt: string) => {
    navigate('/investigator', { state: { prompt } })
  }

  return (
    <div>
      <PageHeader
        title="Good morning — here's your governance posture"
        description={`${formatNumber(summary.totalAssets)} assets under watch across the connected DataHub instance.`}
      />

      {/* KPI row. */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <MetricCard
          label="Metadata Health"
          value={summary.score}
          suffix="/100"
          icon={Activity}
          delta={summary.deltas.score}
        />
        <MetricCard
          label="Healthy Assets"
          value={summary.healthyAssets}
          icon={ShieldCheck}
          delta={summary.deltas.healthyAssets}
          tone="positive"
        />
        <MetricCard
          label="Critical Issues"
          value={summary.criticalIssues}
          icon={TriangleAlert}
          delta={summary.deltas.criticalIssues}
          deltaInverted
          tone="critical"
        />
        <MetricCard
          label="Coverage"
          value={summary.coverage}
          suffix="%"
          icon={GitBranch}
          delta={summary.deltas.coverage}
        />
        <MetricCard
          label="Owners"
          value={summary.owners}
          icon={Users}
          delta={summary.deltas.owners}
        />
      </div>

      {/* Score + critical findings. */}
      <div className="mt-6 grid gap-4 lg:grid-cols-[320px_1fr]">
        <Card className="flex flex-col items-center justify-center gap-2 p-6">
          <HealthScore score={summary.score} />
          <p className="text-muted max-w-[220px] text-center text-[12.5px] leading-relaxed">
            Composite of ownership, documentation, PII classification, and
            freshness across {formatNumber(summary.totalAssets)} assets.
          </p>
        </Card>

        <div>
          <SectionHeader
            title="Critical Findings"
            description="Highest-impact issues detected by the last scan."
          />
          <div className="space-y-4">
            {critical.map((finding) => (
              <RiskCard
                key={finding.id}
                finding={finding}
                onAction={(rec) => askInvestigator(`${rec} for ${finding.assetName}`)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Quick AI actions. */}
      <div className="mt-8">
        <SectionHeader
          title="Quick AI Actions"
          description="One click drops you into a full investigation."
        />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
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

      {/* Findings timeline + agent activity. */}
      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <SectionHeader
            title="Recent AI Findings"
            description="What the agent surfaced, newest first."
          />
          <Timeline items={recentFindings} />
        </Card>

        <Card className="p-5">
          <SectionHeader
            title="Agent Activity"
            description="Scans, fixes, and documentation runs."
          />
          <ActivityFeed events={activityFeed} />
        </Card>
      </div>
    </div>
  )
}
