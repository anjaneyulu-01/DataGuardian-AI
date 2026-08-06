/**
 * Reconstructs the rule engine's arithmetic on the client, so a reader can
 * check the score by hand.
 *
 * This mirrors `backend/app/agents/risk_engine.py` exactly. It does NOT
 * recompute risk — the backend is authoritative and its `risk_score` is what
 * the UI displays. This only explains how that number was reached, which is
 * the difference between an auditable score and a number you must trust.
 *
 * The two rules that matter, both easy to get wrong:
 *
 * 1. A single asset's score is `min(100, sum(points))` — capped, so three
 *    critical findings on one table do not read as 120.
 * 2. A catalogue score is the WORST asset's score, NOT the sum across assets.
 *    Summing would rank a thousand tidy assets below one unowned PII table.
 *
 * Because of (2), findings must be grouped by asset before any total is
 * shown. Adding up every finding in a multi-asset scan would produce a number
 * that appears nowhere in the backend and contradicts the headline score.
 */

import type { ApiFinding, ApiSeverity } from '@/types/api'

/** Mirrors `_BANDS` in risk_engine.py. */
export const RISK_BANDS: { min: number; level: ApiSeverity }[] = [
  { min: 70, level: 'critical' },
  { min: 40, level: 'high' },
  { min: 20, level: 'medium' },
  { min: 0, level: 'low' },
]

/** Mirrors `score_to_level`. */
export function scoreToLevel(score: number): ApiSeverity {
  return RISK_BANDS.find((band) => score >= band.min)?.level ?? 'low'
}

export interface AssetRiskBreakdown {
  assetName: string
  assetUrn: string | null
  findings: ApiFinding[]
  /** Sum of points before the cap — shown when it differs from `score`. */
  rawTotal: number
  /** `min(100, rawTotal)`, matching the engine. */
  score: number
  level: ApiSeverity
  /** True when the cap actually bit, so the UI can explain the difference. */
  capped: boolean
}

export interface RiskBreakdown {
  assets: AssetRiskBreakdown[]
  /** The worst asset's score — how a catalogue-wide verdict is reached. */
  worstScore: number
  /** The asset that set the headline score. */
  worstAsset: AssetRiskBreakdown | null
  /** True when more than one asset contributed findings. */
  multiAsset: boolean
  totalFindings: number
}

/**
 * Group findings by the asset they were raised against and total each one.
 *
 * Findings with no asset attribution are collected under a single bucket
 * rather than dropped: an unattributed finding still contributed to the
 * score, and hiding it would make the arithmetic fail to reconcile.
 */
export function buildRiskBreakdown(findings: ApiFinding[]): RiskBreakdown {
  const byAsset = new Map<string, AssetRiskBreakdown>()

  for (const finding of findings) {
    const key = finding.asset_urn ?? finding.asset_name ?? 'catalogue'
    const existing = byAsset.get(key)

    if (existing) {
      existing.findings.push(finding)
      continue
    }

    byAsset.set(key, {
      assetName: finding.asset_name ?? 'Catalogue-wide',
      assetUrn: finding.asset_urn,
      findings: [finding],
      rawTotal: 0,
      score: 0,
      level: 'low',
      capped: false,
    })
  }

  const assets = [...byAsset.values()].map((asset) => {
    const rawTotal = asset.findings.reduce((sum, f) => sum + f.points, 0)
    const score = Math.min(100, rawTotal)
    return {
      ...asset,
      rawTotal,
      score,
      level: scoreToLevel(score),
      capped: rawTotal > score,
    }
  })

  // Worst first: the asset that set the headline score should lead.
  assets.sort((a, b) => b.score - a.score)

  const worstAsset = assets[0] ?? null

  return {
    assets,
    worstScore: worstAsset?.score ?? 0,
    worstAsset,
    multiAsset: assets.length > 1,
    totalFindings: findings.length,
  }
}
