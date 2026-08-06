import { motion } from 'framer-motion'
import { ArrowRight, CircleCheck, Clock, ShieldAlert, Sparkles } from 'lucide-react'

import { SourceTag } from './SourceTag'
import type { DataSource } from '@/services'
import type { OverviewMetrics } from '@/services/overviewService'
import { cn } from '@/utils'
import { formatNumber } from '@/utils/format'

interface ScanBriefProps {
  metrics: OverviewMetrics
  source: DataSource
  reason?: string
  /** When the underlying query last resolved. */
  readAt: number | null
  onAsk: (prompt: string) => void
}

/**
 * The opening brief — the agent reporting, rather than a wall of tiles.
 *
 * Every sentence is assembled from measured values. There is deliberately no
 * "health improved by 4%" and no "hours saved": both require scan history the
 * system does not persist, so either would be invented. The one temporal
 * claim made here — when the catalogue was read — is taken from the query's
 * own resolution time, which is a fact the client actually knows.
 *
 * The narrative is composed by rules, not by a model. It is the first thing a
 * visitor reads, so it must say the same thing every time for the same
 * catalogue.
 */
export function ScanBrief({
  metrics,
  source,
  reason,
  readAt,
  onAsk,
}: ScanBriefProps) {
  const headline = buildHeadline(metrics)
  const findings = buildFindings(metrics)

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="card overflow-hidden"
    >
      <div className="border-line bg-raised/40 flex flex-wrap items-center gap-2.5 border-b px-5 py-3">
        <Sparkles className="text-brand-strong size-4" />
        <p className="text-ink text-[13px] font-semibold">
          Governance scan complete
        </p>
        {readAt ? (
          <span className="text-faint inline-flex items-center gap-1 text-[11.5px]">
            <Clock className="size-3" />
            catalogue read {relativeTime(readAt)}
          </span>
        ) : null}
        <span className="ml-auto">
          <SourceTag source={source} reason={reason} />
        </span>
      </div>

      <div className="p-5">
        <p className="text-ink text-[15px] leading-relaxed font-medium">{headline}</p>

        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {findings.map((finding) => (
            <li
              key={finding.label}
              className={cn(
                'flex items-start gap-2.5 rounded-lg border px-3 py-2.5',
                finding.tone === 'critical'
                  ? 'border-critical/25 bg-critical/8'
                  : finding.tone === 'warning'
                    ? 'border-warning/25 bg-warning/8'
                    : 'border-line bg-raised/40',
              )}
            >
              <span
                className={cn(
                  'mt-0.5 shrink-0',
                  finding.tone === 'critical'
                    ? 'text-critical'
                    : finding.tone === 'warning'
                      ? 'text-warning'
                      : 'text-positive',
                )}
              >
                {finding.tone === 'positive' ? (
                  <CircleCheck className="size-4" />
                ) : (
                  <ShieldAlert className="size-4" />
                )}
              </span>
              <div className="min-w-0">
                <p className="text-ink text-[13px] font-semibold tabular-nums">
                  {finding.label}
                </p>
                <p className="text-muted mt-0.5 text-[11.5px] leading-snug">
                  {finding.detail}
                </p>
              </div>
            </li>
          ))}
        </ul>

        {/* Every action opens a real agent investigation. Nothing here is a
            placeholder — an action that cannot execute is not offered. */}
        <div className="mt-4 flex flex-wrap gap-2">
          {buildActions(metrics).map((action, index) => (
            <button
              key={action.prompt}
              type="button"
              onClick={() => onAsk(action.prompt)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12.5px] font-medium transition-all',
                index === 0
                  ? 'bg-brand hover:bg-brand-strong shadow-glow text-white'
                  : 'border-line bg-raised text-ink-secondary hover:border-brand/40 hover:text-ink border',
              )}
            >
              {action.label}
              <ArrowRight className="size-3.5" />
            </button>
          ))}
        </div>
      </div>
    </motion.section>
  )
}

/** One sentence stating what was scanned and the headline conclusion. */
function buildHeadline(m: OverviewMetrics): string {
  const assets = `${formatNumber(m.totalAssets)} ${m.totalAssets === 1 ? 'asset' : 'assets'}`

  if (m.criticalIssues > 0) {
    return `I analysed ${assets} and found ${m.criticalIssues} at critical risk. Ownership and classification gaps are the largest contributors.`
  }
  if (m.missingOwners > 0) {
    return `I analysed ${assets}. Nothing is at critical risk, but ${m.missingOwners} ${m.missingOwners === 1 ? 'asset has' : 'assets have'} no accountable owner.`
  }
  if (m.documentationCoverage < 80) {
    return `I analysed ${assets}. Ownership is complete; documentation coverage is ${m.documentationCoverage}% and is now the weakest signal.`
  }
  return `I analysed ${assets} and found no critical governance gaps. Metadata health is ${m.score}/100.`
}

interface BriefFinding {
  label: string
  detail: string
  tone: 'critical' | 'warning' | 'positive'
}

/** Measured figures only — each is a count or a ratio the service computed. */
function buildFindings(m: OverviewMetrics): BriefFinding[] {
  return [
    {
      label: `${m.criticalIssues} critical ${m.criticalIssues === 1 ? 'risk' : 'risks'}`,
      detail:
        m.criticalIssues > 0
          ? 'Assets scoring 70 or above on the deterministic rule engine'
          : 'No asset scored 70 or above',
      tone: m.criticalIssues > 0 ? 'critical' : 'positive',
    },
    {
      label: `${m.missingOwners} without an owner`,
      detail:
        m.missingOwners > 0
          ? 'No accountable responder when these break'
          : `All assets have an owner across ${m.owners} people and groups`,
      tone: m.missingOwners > 0 ? 'warning' : 'positive',
    },
    {
      label: `${m.documentationCoverage}% documented`,
      detail: `Assets carrying a description · ${m.domainCount} business ${m.domainCount === 1 ? 'domain' : 'domains'}`,
      tone: m.documentationCoverage >= 80 ? 'positive' : 'warning',
    },
    {
      label: `${m.score}/100 metadata health`,
      detail: `Composite of ownership, documentation, and classification · ${m.healthyAssets} assets above 80`,
      tone: m.score >= 80 ? 'positive' : m.score >= 50 ? 'warning' : 'critical',
    },
  ]
}

/** Actions ordered by what the scan actually found. */
function buildActions(m: OverviewMetrics): { label: string; prompt: string }[] {
  const actions: { label: string; prompt: string }[] = []

  if (m.criticalIssues > 0) {
    actions.push({
      label: 'Investigate critical risks',
      prompt: 'Which datasets are highest risk?',
    })
  }
  if (m.missingOwners > 0) {
    actions.push({
      label: `Review ${m.missingOwners} unowned ${m.missingOwners === 1 ? 'asset' : 'assets'}`,
      prompt: 'Find datasets without owners',
    })
  }
  actions.push({ label: 'Scan for untagged PII', prompt: 'Find untagged PII across all datasets' })
  actions.push({ label: 'Generate executive report', prompt: 'Create a governance report' })

  return actions.slice(0, 4)
}

/** Coarse relative time. Precision beyond a minute is noise here. */
function relativeTime(timestamp: number): string {
  const seconds = Math.round((Date.now() - timestamp) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  return `${hours}h ago`
}
