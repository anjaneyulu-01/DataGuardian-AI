/**
 * The AI Investigator's connection to the LangGraph agent.
 *
 * Live source: `POST /api/v1/agent/analyze`.
 *
 * The backend always answers 200 for a completed run — including a degraded
 * one — so a non-2xx here means a genuine request or transport problem. A
 * degraded result is passed through with its `degraded` flag intact rather
 * than being retried or hidden: the user needs to know the answer was built
 * on partial evidence.
 */

import { apiClient } from './apiClient'
import { withFallback, type Sourced } from './fallback'
import { aiAnswers, fallbackAnswer } from '@/data/mockData'
import type { ApiAgentResult } from '@/types/api'
import type { AIAnswer, EvidenceItem, Severity } from '@/types/domain'

/** Agent runs are multi-step and call an LLM; they are slow by nature. */
const ANALYZE_TIMEOUT_MS = 180_000

/**
 * The full agent result plus the view model the UI renders.
 *
 * Both are kept: `answer` drives the existing `AIResponse` component, while
 * `raw` carries the trace, tools used, and provider that only the agent can
 * supply.
 */
export interface Investigation {
  answer: AIAnswer
  /**
   * The full agent payload. `null` only in the demo fallback, where there was
   * no agent run — so a `null` here means "no trace to show", not "empty
   * trace".
   */
  raw: ApiAgentResult | null
}

export async function analyzeQuestion(question: string): Promise<Sourced<Investigation>> {
  return withFallback<Investigation>(
    async () => {
      const { data } = await apiClient.post<ApiAgentResult>(
        '/v1/agent/analyze',
        { question },
        { timeout: ANALYZE_TIMEOUT_MS },
      )
      return { answer: toAIAnswer(data), raw: data }
    },
    () => ({ answer: matchDemoAnswer(question), raw: null }),
    'agentService.analyze',
  )
}

/**
 * Map the agent result onto the presentation model.
 *
 * The mapping is deliberate about provenance: `reasoning` comes from the
 * execution trace (what the agent actually did), `risk` and `evidence` from
 * the deterministic rule engine, and only `recommendation` from LLM prose.
 */
export function toAIAnswer(result: ApiAgentResult): AIAnswer {
  return {
    id: result.intent,
    question: result.question,
    reasoning: buildReasoning(result),
    risk: {
      level: result.risk_level as Severity,
      statement: result.business_impact || result.summary,
    },
    evidence: buildEvidence(result),
    recommendation: result.summary,
    actions: result.recommendations.map((r) => r.action).slice(0, 4),
  }
}

/** Turn the node trace into human-readable reasoning steps. */
function buildReasoning(result: ApiAgentResult): string[] {
  const NODE_LABELS: Record<string, string> = {
    planner: 'Classified the question and selected which tools to run',
    datasets: 'Retrieved dataset metadata from DataHub',
    owners: 'Resolved ownership records',
    lineage: 'Traced upstream and downstream lineage',
    statistics: 'Collected profiling and usage statistics',
    risk: 'Applied deterministic governance rules',
    reasoning: 'Explained the findings',
    recommendation: 'Derived corrective actions',
    report: 'Formatted the governance report',
  }

  const steps = result.trace
    .filter((entry) => entry.status === 'ok')
    .map((entry) => {
      const label = NODE_LABELS[entry.node] ?? entry.node
      return `${label} (${Math.round(entry.duration_ms)}ms)`
    })

  if (result.degraded && result.errors.length > 0) {
    steps.push(`Partial evidence: ${result.errors[0]}`)
  }
  return steps
}

/** Findings become evidence rows; the agent's own evidence fills any gap. */
function buildEvidence(result: ApiAgentResult): EvidenceItem[] {
  if (result.findings.length > 0) {
    return result.findings.slice(0, 8).map((finding) => ({
      label: finding.asset_name ?? finding.rule,
      value: `${finding.title} (+${finding.points})`,
      severity: finding.severity as Severity,
    }))
  }

  return result.evidence.slice(0, 8).map((item) => ({
    label: String(item.name ?? item.urn ?? 'asset'),
    value: describeEvidence(item),
  }))
}

function describeEvidence(item: Record<string, unknown>): string {
  const parts: string[] = []
  const owners = item.owners
  if (Array.isArray(owners)) {
    parts.push(owners.length > 0 ? `owned by ${owners[0]}` : 'no owner')
  }
  if (item.has_description === false) parts.push('undocumented')
  if (typeof item.downstream_count === 'number') {
    parts.push(`${item.downstream_count} downstream`)
  }
  return parts.join(' · ') || 'no issues found'
}

/** Keyword-match a demo answer when the backend is unreachable. */
function matchDemoAnswer(question: string): AIAnswer {
  const lowered = question.toLowerCase()
  const byId = (id: string) =>
    aiAnswers.find((answer) => answer.id === id) ?? fallbackAnswer

  if (lowered.includes('owner')) return { ...byId('missing-owners'), question }
  if (lowered.includes('risk')) return { ...byId('highest-risk'), question }
  if (lowered.includes('impact') || lowered.includes('downstream'))
    return { ...byId('downstream-impact'), question }
  if (lowered.includes('document') || lowered.includes('docs'))
    return { ...byId('generate-docs'), question }
  return { ...fallbackAnswer, question }
}
