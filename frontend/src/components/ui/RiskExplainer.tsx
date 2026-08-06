import { AnimatePresence, motion } from 'framer-motion'
import { Calculator, ChevronRight, Database, FileWarning, Scale } from 'lucide-react'
import { useState } from 'react'

import { RiskBadge } from './RiskBadge'
import { ruleDoc } from '@/data/riskRules'
import type { ApiFinding } from '@/types/api'
import type { Severity } from '@/types/domain'
import { cn } from '@/utils'
import { buildRiskBreakdown, type AssetRiskBreakdown } from '@/utils/riskMath'

interface RiskExplainerProps {
  findings: ApiFinding[]
  /** The backend's authoritative score. Never recomputed here. */
  riskScore: number
  riskLevel: string
}

/**
 * The deterministic score, shown as arithmetic rather than asserted.
 *
 * This is the visual form of the product's central claim. The backend
 * computes `risk_score`; this panel shows the addition that produced it, so a
 * steward can disagree with a *weight* rather than with a black box.
 *
 * Two behaviours are deliberate:
 *
 * * The backend score is displayed verbatim. The client sum is shown beside
 *   it as a check, and a mismatch is surfaced rather than hidden — if these
 *   ever diverge, the honest move is to say so.
 * * Findings are grouped by asset, because a catalogue verdict is the worst
 *   asset's score and not the sum. Showing one flat total would print a
 *   number that exists nowhere in the backend.
 */
export function RiskExplainer({ findings, riskScore, riskLevel }: RiskExplainerProps) {
  const breakdown = buildRiskBreakdown(findings)

  if (findings.length === 0) {
    return (
      <div className="border-line rounded-xl border p-4">
        <p className="text-ink text-[13px] font-semibold">
          No governance rules triggered
        </p>
        <p className="text-muted mt-1 text-[12px] leading-relaxed">
          The rule engine ran over the retrieved metadata and found no
          violations, so the risk score is {riskScore}.
        </p>
      </div>
    )
  }

  // Reconciliation check. The catalogue verdict is the worst asset's score.
  const reconciles = breakdown.worstScore === riskScore

  return (
    <div>
      {/* How the headline number was reached. */}
      <div className="border-line bg-raised/40 rounded-xl border p-4">
        <div className="flex flex-wrap items-center gap-2.5">
          <Calculator className="text-brand-strong size-4" />
          <p className="text-ink text-[13px] font-semibold">
            How this score was calculated
          </p>
          <span className="ml-auto flex items-center gap-2">
            <span className="text-ink text-lg font-semibold tabular-nums">
              {riskScore}
            </span>
            <span className="text-faint text-[12px]">/100</span>
            <RiskBadge severity={riskLevel as Severity} size="sm" />
          </span>
        </div>

        <p className="text-muted mt-2 text-[12px] leading-relaxed">
          {breakdown.multiAsset ? (
            <>
              {breakdown.totalFindings} findings across {breakdown.assets.length}{' '}
              assets. A catalogue score is the <strong>worst asset's</strong>{' '}
              score, not the sum — otherwise a large tidy catalogue would rank
              worse than a small dangerous one.
            </>
          ) : (
            <>
              {breakdown.totalFindings}{' '}
              {breakdown.totalFindings === 1 ? 'rule' : 'rules'} triggered on{' '}
              {breakdown.worstAsset?.assetName}. Points are summed and capped at
              100.
            </>
          )}
        </p>

        {/* The band table — what the number means. */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {[
            { label: 'Low', range: '0–19' },
            { label: 'Medium', range: '20–39' },
            { label: 'High', range: '40–69' },
            { label: 'Critical', range: '70+' },
          ].map((band) => {
            const active = band.label.toLowerCase() === riskLevel.toLowerCase()
            return (
              <span
                key={band.label}
                className={cn(
                  'rounded-md border px-2 py-1 text-[10.5px] font-medium tabular-nums',
                  active
                    ? 'border-brand/40 bg-brand/12 text-ink'
                    : 'border-line bg-surface text-faint',
                )}
              >
                {band.label} {band.range}
              </span>
            )
          })}
        </div>

        {!reconciles ? (
          <p className="text-warning mt-2.5 text-[11.5px] leading-relaxed">
            Client-side check: the worst asset totals {breakdown.worstScore}, but
            the API reported {riskScore}. The API value is authoritative and is
            what is shown above.
          </p>
        ) : null}
      </div>

      {/* Per-asset arithmetic. */}
      <div className="mt-3 space-y-2.5">
        {breakdown.assets.map((asset, index) => (
          <AssetBreakdown
            key={asset.assetUrn ?? asset.assetName}
            asset={asset}
            setsHeadline={index === 0 && breakdown.multiAsset}
          />
        ))}
      </div>
    </div>
  )
}

function AssetBreakdown({
  asset,
  setsHeadline,
}: {
  asset: AssetRiskBreakdown
  setsHeadline: boolean
}) {
  return (
    <div className="border-line overflow-hidden rounded-xl border">
      <div className="bg-raised/40 flex flex-wrap items-center gap-2 px-3.5 py-2.5">
        <Database className="text-faint size-3.5 shrink-0" />
        <p className="text-ink truncate text-[12.5px] font-semibold">
          {asset.assetName}
        </p>
        {setsHeadline ? (
          <span className="border-brand/30 bg-brand/10 text-brand-strong rounded-md border px-1.5 py-0.5 text-[10px] font-medium">
            Sets the score
          </span>
        ) : null}
        <span className="ml-auto flex items-center gap-2">
          <span className="text-ink text-[13px] font-semibold tabular-nums">
            {asset.score}
          </span>
          <RiskBadge severity={asset.level as Severity} size="sm" />
        </span>
      </div>

      <ul className="divide-line divide-y">
        {asset.findings.map((finding, index) => (
          <FindingRow key={`${finding.rule}-${index}`} finding={finding} />
        ))}
      </ul>

      {/* The addition, written out. */}
      <div className="border-line bg-surface flex flex-wrap items-center gap-x-2 gap-y-1 border-t px-3.5 py-2.5">
        <Scale className="text-faint size-3.5" />
        <span className="text-muted font-mono text-[11.5px] tabular-nums">
          {asset.findings.map((f) => f.points).join(' + ')} = {asset.rawTotal}
        </span>
        {asset.capped ? (
          <span className="text-warning text-[11px]">
            capped at 100 (raw total {asset.rawTotal})
          </span>
        ) : null}
        <span className="text-faint ml-auto text-[11px]">
          {asset.score} → {asset.level}
        </span>
      </div>
    </div>
  )
}

/** One rule, expandable into the policy behind it. */
function FindingRow({ finding }: { finding: ApiFinding }) {
  const [open, setOpen] = useState(false)
  const doc = ruleDoc(finding.rule)

  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="hover:bg-raised/40 flex w-full items-start gap-2.5 px-3.5 py-2.5 text-left transition-colors"
      >
        <ChevronRight
          className={cn(
            'text-faint mt-0.5 size-3.5 shrink-0 transition-transform',
            open && 'rotate-90',
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-ink text-[12.5px] font-medium">
              {finding.title}
            </span>
            <code className="text-faint bg-raised rounded px-1.5 py-0.5 font-mono text-[10.5px]">
              {finding.rule}
            </code>
          </div>
          <p className="text-muted mt-0.5 text-[12px] leading-relaxed">
            {finding.detail}
          </p>
        </div>
        <span className="text-ink shrink-0 text-[12.5px] font-semibold tabular-nums">
          +{finding.points}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <dl className="bg-raised/30 space-y-2.5 px-3.5 pt-1 pb-3.5 pl-9">
              <ExplainRow label="Why this weight" value={doc.rationale} />
              <ExplainRow label="Metadata used" value={doc.metadataUsed} mono />
              <ExplainRow label="Business impact" value={doc.consequence} />
              <ExplainRow
                label="Severity"
                value={`${finding.severity} · contributes ${finding.points} points`}
              />
            </dl>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </li>
  )
}

function ExplainRow({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div>
      <dt className="text-faint text-[10px] font-semibold tracking-widest uppercase">
        {label}
      </dt>
      <dd
        className={cn(
          'text-ink-secondary mt-0.5 text-[12px] leading-relaxed',
          mono && 'font-mono text-[11.5px]',
        )}
      >
        {value}
      </dd>
    </div>
  )
}

/** Icon export kept for the empty-state variant used by callers. */
export const RiskExplainerIcon = FileWarning
