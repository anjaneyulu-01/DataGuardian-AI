import { ArrowRight, UserX } from 'lucide-react'
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

import { Card, PageHeader, SectionHeader, StatusBadge } from '@/components/ui'
import { useCountUp } from '@/hooks/useCountUp'
import { riskTrend, severityCounts, topRiskAssets } from '@/data/mockData'
import type { Severity } from '@/types/domain'
import { cn } from '@/utils'
import { SEVERITY, SEVERITY_ORDER } from '@/utils/severity'

/** Risk posture: distribution, 2-week trend, and the assets driving it. */
export function RiskCenterPage() {
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader
        title="Risk Center"
        description="Where governance risk is concentrated, and whether it is trending the right way."
      />

      {/* Severity distribution. */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {SEVERITY_ORDER.map((severity) => (
          <SeverityCard
            key={severity}
            severity={severity}
            count={severityCounts[severity]}
          />
        ))}
      </div>

      {/* Trend. */}
      <Card className="mt-6 p-5">
        <SectionHeader
          title="Risk Trend"
          description="Open findings by severity over the last two weeks."
        />
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={riskTrend} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
              <defs>
                {SEVERITY_ORDER.map((severity) => (
                  <linearGradient
                    key={severity}
                    id={`grad-${severity}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="0%" stopColor={SEVERITY[severity].hex} stopOpacity={0.28} />
                    <stop offset="100%" stopColor={SEVERITY[severity].hex} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid stroke="var(--t-line)" strokeDasharray="0" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="var(--t-faint)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                dy={6}
              />
              <YAxis stroke="var(--t-faint)" fontSize={11} tickLine={false} axisLine={false} />
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
              {/* Draw low→critical so critical sits on top visually. */}
              {[...SEVERITY_ORDER].reverse().map((severity) => (
                <Area
                  key={severity}
                  type="monotone"
                  dataKey={severity}
                  name={SEVERITY[severity].label}
                  stroke={SEVERITY[severity].hex}
                  strokeWidth={1.75}
                  fill={`url(#grad-${severity})`}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Top risk assets. */}
      <div className="mt-6">
        <SectionHeader
          title="Top Risk Assets"
          description="Lowest composite health across the catalogue — fix these first."
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
        <div className="space-y-2.5">
          {topRiskAssets.map((asset, index) => (
            <Card key={asset.urn} interactive className="flex items-center gap-4 px-4 py-3">
              <span className="text-faint w-5 text-center font-mono text-[12px] tabular-nums">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-ink truncate text-[13px] font-semibold">{asset.name}</p>
                <p className="text-faint text-[11.5px]">
                  {asset.platform} · {asset.domain} · {asset.downstreamCount} downstream
                </p>
              </div>
              {!asset.owner ? (
                <span className="text-critical hidden items-center gap-1 text-[11.5px] font-medium sm:flex">
                  <UserX className="size-3.5" /> Unowned
                </span>
              ) : null}
              <StatusBadge severity={asset.severity} />
              <HealthDial value={asset.health} />
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}

function SeverityCard({ severity, count }: { severity: Severity; count: number }) {
  const style = SEVERITY[severity]
  const animated = useCountUp(count)

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
      <p className="text-muted mt-1 text-[12px]">open findings</p>
    </Card>
  )
}

/** Small circular health indicator for list rows. */
function HealthDial({ value }: { value: number }) {
  const severity =
    value < 40 ? 'critical' : value < 60 ? 'high' : value < 80 ? 'medium' : 'low'
  const radius = 14
  const circumference = 2 * Math.PI * radius

  return (
    <div className="relative hidden size-9 sm:block" title={`Health ${value}%`}>
      <svg viewBox="0 0 36 36" className="-rotate-90">
        <circle cx="18" cy="18" r={radius} fill="none" stroke="var(--t-line)" strokeWidth="3.5" />
        <circle
          cx="18"
          cy="18"
          r={radius}
          fill="none"
          stroke={SEVERITY[severity].hex}
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - value / 100)}
        />
      </svg>
      <span className="text-ink absolute inset-0 grid place-items-center text-[9.5px] font-semibold tabular-nums">
        {value}
      </span>
    </div>
  )
}
