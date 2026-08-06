/**
 * Executive report generation.
 *
 * Markdown rather than PDF, deliberately: Markdown renders in GitHub, Slack,
 * Notion, and every code review tool, diffs cleanly, and needs no rendering
 * dependency in the bundle. A PDF would add a large client-side library to
 * produce a format nobody reviews governance in.
 *
 * Every value in the output is read from the agent response. Nothing is
 * estimated, extrapolated, or rounded up — the report is intended to be
 * pasted into a ticket, so a fabricated number here would travel further than
 * one on screen.
 */

import type { ApiAgentResult } from '@/types/api'
import { buildRiskBreakdown } from './riskMath'

export interface ReportOptions {
  /** Whether the underlying data came from a live backend or Demo Mode. */
  source: 'live' | 'demo'
  /** Generation timestamp. Injectable so tests are deterministic. */
  now?: Date
}

export function buildExecutiveReport(
  result: ApiAgentResult,
  { source, now = new Date() }: ReportOptions,
): string {
  const breakdown = buildRiskBreakdown(result.findings)
  const lines: string[] = []

  lines.push('# Governance Assessment')
  lines.push('')

  // Provenance first. A report that does not say where its data came from is
  // worse than no report, and this is the line a reader will check.
  if (source === 'demo') {
    lines.push(
      '> **Demo data.** This report was generated from the built-in ' +
        'demonstration catalogue, not from a live DataHub instance.',
    )
  } else {
    lines.push('> Generated from live DataHub metadata.')
  }
  lines.push('')

  lines.push(`**Question:** ${result.question}`)
  lines.push('')
  lines.push(`| | |`)
  lines.push(`| --- | --- |`)
  lines.push(`| Risk level | **${result.risk_level.toUpperCase()}** |`)
  lines.push(`| Risk score | ${result.risk_score} / 100 |`)
  lines.push(`| Findings | ${result.findings.length} |`)
  lines.push(`| Assets with findings | ${breakdown.assets.length} |`)
  lines.push(`| Intent classified as | \`${result.intent}\` |`)
  lines.push(`| Analysis duration | ${Math.round(result.duration_ms)} ms |`)
  if (result.llm_provider) {
    lines.push(`| Reasoning provider | ${result.llm_provider} |`)
  }
  lines.push(`| Generated | ${now.toISOString()} |`)
  if (result.degraded) {
    lines.push(`| Status | **Degraded — partial evidence** |`)
  }
  lines.push('')

  // --- Summary -------------------------------------------------------------
  if (result.summary) {
    lines.push('## Executive summary')
    lines.push('')
    lines.push(result.summary)
    lines.push('')
  }

  if (result.business_impact) {
    lines.push('## Business impact')
    lines.push('')
    lines.push(result.business_impact)
    lines.push('')
  }

  // --- Findings ------------------------------------------------------------
  if (result.findings.length > 0) {
    lines.push('## Findings')
    lines.push('')
    lines.push(
      'Scores are produced by a deterministic rule engine, not by a language ' +
        'model. Each rule contributes a fixed weight, so the arithmetic below ' +
        'can be checked by hand.',
    )
    lines.push('')

    for (const asset of breakdown.assets) {
      lines.push(`### ${asset.assetName}`)
      lines.push('')
      if (asset.assetUrn) {
        lines.push(`\`${asset.assetUrn}\``)
        lines.push('')
      }
      lines.push('| Rule | Severity | Points | Detail |')
      lines.push('| --- | --- | ---: | --- |')
      for (const finding of asset.findings) {
        // Pipes inside a cell would break the table.
        const detail = finding.detail.replace(/\|/g, '\\|')
        lines.push(
          `| \`${finding.rule}\` | ${finding.severity} | ${finding.points} | ${detail} |`,
        )
      }
      const sum = asset.findings.map((f) => f.points).join(' + ')
      lines.push(
        `| | | **${asset.score}** | ${sum} = ${asset.rawTotal}` +
          (asset.capped ? ' (capped at 100)' : '') +
          ` → **${asset.level}** |`,
      )
      lines.push('')
    }

    if (breakdown.multiAsset) {
      lines.push(
        `> The catalogue score (**${result.risk_score}**) is the worst ` +
          `asset's score, not the sum across assets.`,
      )
      lines.push('')
    }
  }

  // --- Recommendations -----------------------------------------------------
  if (result.recommendations.length > 0) {
    lines.push('## Recommendations')
    lines.push('')
    for (const [index, rec] of result.recommendations.entries()) {
      lines.push(`${index + 1}. **${rec.action}** — _${rec.priority}_`)
      if (rec.rationale) lines.push(`   ${rec.rationale}`)
    }
    lines.push('')
  }

  if (result.next_steps.length > 0) {
    lines.push('## Next steps')
    lines.push('')
    for (const step of result.next_steps) lines.push(`- ${step}`)
    lines.push('')
  }

  // --- Execution -----------------------------------------------------------
  lines.push('## How this was produced')
  lines.push('')
  lines.push('| Stage | Status | Duration |')
  lines.push('| --- | --- | ---: |')
  for (const entry of result.trace) {
    lines.push(
      `| ${entry.node} | ${entry.status} | ${Math.round(entry.duration_ms)} ms |`,
    )
  }
  lines.push('')

  if (result.errors.length > 0) {
    lines.push('### Errors encountered')
    lines.push('')
    for (const error of result.errors) lines.push(`- ${error}`)
    lines.push('')
  }

  lines.push('---')
  lines.push('')
  lines.push(
    '_Generated by DataGuardian AI. Risk scores are deterministic and ' +
      'reproducible; narrative sections are model-generated from the ' +
      'evidence above._',
  )
  lines.push('')

  return lines.join('\n')
}

/** Filename for a downloaded report, safe on every platform. */
export function reportFilename(result: ApiAgentResult, now = new Date()): string {
  const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, '-')
  return `dataguardian-${result.intent}-${stamp}.md`
}

/**
 * Trigger a client-side download.
 *
 * Kept out of the builder so the report text stays a pure function that tests
 * can assert on without touching the DOM.
 */
export function downloadMarkdown(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}
