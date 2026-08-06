import {
  AlertTriangle,
  ClockAlert,
  Copy,
  FileBarChart,
  ScanSearch,
  ShieldAlert,
  Unlink,
  UserX,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router'

import { AgentTrace } from '@/components/ui/AgentTrace'
import {
  AIResponse,
  AnalysisDetail,
  Card,
  LoadingState,
  PageHeader,
  PromptInput,
  RecommendationCard,
  SectionHeader,
  SourceTag,
} from '@/components/ui'
import { useAnalyze } from '@/hooks/queries'
import type { ApiAgentResult } from '@/types/api'
import type { AIAnswer, Recommendation } from '@/types/domain'
import type { DataSource } from '@/services'

const ACTION_ICONS: Record<string, LucideIcon> = {
  'missing-owners': UserX,
  'broken-lineage': Unlink,
  duplicates: Copy,
  pii: ShieldAlert,
  report: FileBarChart,
  stale: ClockAlert,
}

/** The suggested-action cards. Each maps to a real agent intent. */
const SUGGESTED = [
  {
    id: 'missing-owners',
    title: 'Missing Owners',
    description: 'Assets with no accountable owner, ranked by blast radius.',
    prompt: 'Find datasets without owners',
  },
  {
    id: 'broken-lineage',
    title: 'Broken Lineage',
    description: 'Assets whose upstream sources have drifted or vanished.',
    prompt: 'Show assets with broken or missing lineage',
  },
  {
    id: 'duplicates',
    title: 'Duplicate Assets',
    description: 'Near-identical tables splitting the source of truth.',
    prompt: 'Find duplicate or near-identical datasets',
  },
  {
    id: 'pii',
    title: 'PII Detection',
    description: 'Probable personal data missing a classification tag.',
    prompt: 'Find untagged PII across all datasets',
  },
  {
    id: 'report',
    title: 'Generate Report',
    description: 'An executive governance summary of the whole catalogue.',
    prompt: 'Create a governance report',
  },
  {
    id: 'stale',
    title: 'Stale Assets',
    description: 'Datasets not refreshed within their expected cadence.',
    prompt: 'Which assets are stale?',
  },
] as const

const EXAMPLES = [
  'Find datasets without owners',
  'Which datasets are highest risk?',
  'Explain downstream impact',
  'Generate documentation',
  'Analyze lineage',
]

interface Exchange {
  id: number
  answer: AIAnswer
  raw: ApiAgentResult | null
  source: DataSource
  reason?: string
}

/**
 * The AI Investigator — the product's hero surface.
 *
 * Every question is a real `POST /api/v1/agent/analyze` call. The agent plans
 * which tools to run, gathers evidence, scores risk deterministically, and
 * explains the result; this page renders that, including the execution trace
 * so the multi-step work is visible rather than claimed.
 */
export function InvestigatorPage() {
  const location = useLocation()
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const nextId = useRef(1)
  const bottomRef = useRef<HTMLDivElement>(null)
  const firedFor = useRef<string | null>(null)

  const analyze = useAnalyze()

  const ask = (question: string) => {
    if (analyze.isPending) return

    analyze.mutate(question, {
      onSuccess: (result) => {
        setExchanges((current) => [
          ...current,
          {
            id: nextId.current++,
            answer: result.data.answer,
            raw: result.data.raw,
            source: result.source,
            reason: result.reason,
          },
        ])
      },
    })
  }

  // A prompt handed over from another page (Overview quick actions).
  useEffect(() => {
    const handed = (location.state as { prompt?: string } | null)?.prompt
    if (handed && firedFor.current !== handed) {
      firedFor.current = handed
      ask(handed)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [exchanges.length, analyze.isPending])

  const started = exchanges.length > 0 || analyze.isPending

  return (
    <div className="mx-auto max-w-3xl">
      {!started ? (
        <div className="pt-8 pb-4 text-center sm:pt-16">
          <h1 className="text-ink text-2xl font-semibold tracking-tight sm:text-3xl">
            Ask DataGuardian
          </h1>
          <p className="text-muted mx-auto mt-2 mb-8 max-w-md text-sm leading-relaxed">
            Your autonomous metadata governance engineer. Every answer is
            grounded in live DataHub metadata and a deterministic rule engine —
            never a guess.
          </p>
        </div>
      ) : (
        <PageHeader
          title="AI Investigator"
          description="The agent plans its own tools, gathers evidence, then explains what it found."
        />
      )}

      <PromptInput
        size={started ? 'default' : 'hero'}
        placeholder="Ask DataGuardian about your metadata..."
        onSubmit={ask}
        disabled={analyze.isPending}
        examples={started ? [] : EXAMPLES}
      />

      {!started ? (
        <div className="mt-10">
          <SectionHeader title="Suggested AI Actions" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {SUGGESTED.map((action) => {
              const Icon = ACTION_ICONS[action.id] ?? ScanSearch
              return (
                <Card
                  key={action.id}
                  interactive
                  onClick={() => ask(action.prompt)}
                  className="group flex flex-col gap-2.5 p-4"
                >
                  <span className="border-line bg-raised text-muted group-hover:border-brand/30 group-hover:text-brand-strong grid size-8 place-items-center rounded-lg border transition-colors">
                    <Icon className="size-4" strokeWidth={2} />
                  </span>
                  <div>
                    <p className="text-ink text-[13px] font-semibold">{action.title}</p>
                    <p className="text-muted mt-0.5 text-[12px] leading-snug">
                      {action.description}
                    </p>
                  </div>
                </Card>
              )
            })}
          </div>
        </div>
      ) : null}

      <div className="mt-6 space-y-5">
        {exchanges.map((exchange) => (
          <div key={exchange.id}>
            {/* Degradation and demo-data warnings sit ABOVE the answer, so
                they cannot be missed after reading it. */}
            {exchange.source === 'demo' ? (
              <Banner
                tone="warning"
                text="Backend unreachable — showing an illustrative answer, not your catalogue."
                detail={exchange.reason}
              />
            ) : exchange.raw?.degraded ? (
              <Banner
                tone="warning"
                text="Partial evidence: some tools failed, so this answer is incomplete."
                detail={exchange.raw.errors[0]}
              />
            ) : null}

            <AIResponse
              answer={exchange.answer}
              onAction={ask}
              footer={
                exchange.raw ? (
                  <AgentTrace
                    trace={exchange.raw.trace}
                    toolsUsed={exchange.raw.tools_used}
                    durationMs={exchange.raw.duration_ms}
                    provider={exchange.raw.llm_provider}
                  />
                ) : null
              }
            />

            {/* The evidence panel: score arithmetic, execution pipeline, and
                business impact. Always shown — these are the features that
                distinguish an agent from a chatbot, and a judge or steward
                will not go looking for them behind a toggle. */}
            {exchange.raw ? (
              <AnalysisDetail result={exchange.raw} source={exchange.source} />
            ) : null}

            {exchange.raw && exchange.raw.recommendations.length > 0 ? (
              <div className="mt-4">
                <SectionHeader
                  title="Recommendations"
                  action={<SourceTag source={exchange.source} reason={exchange.reason} />}
                />
                <div className="space-y-2.5">
                  {exchange.raw.recommendations.map((recommendation, index) => (
                    <RecommendationCard
                      key={`${recommendation.action}-${index}`}
                      index={index}
                      recommendation={toRecommendation(recommendation)}
                      onRun={(r) => ask(r.action)}
                    />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ))}

        {analyze.isPending ? (
          <LoadingState
            variant="thinking"
            label="Planning tools, gathering evidence, scoring risk…"
          />
        ) : null}

        {analyze.isError ? (
          <Banner
            tone="critical"
            text="The investigation could not be completed."
            detail={analyze.error.message}
          />
        ) : null}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function toRecommendation(raw: ApiAgentResult['recommendations'][number]): Recommendation {
  return {
    action: raw.action,
    rationale: raw.rationale,
    priority: raw.priority,
    assetUrn: raw.asset_urn,
  }
}

function Banner({
  tone,
  text,
  detail,
}: {
  tone: 'warning' | 'critical'
  text: string
  detail?: string
}) {
  return (
    <div
      role="status"
      className={
        tone === 'critical'
          ? 'border-critical/25 bg-critical/10 mb-3 flex items-start gap-2.5 rounded-xl border p-3'
          : 'border-warning/25 bg-warning/10 mb-3 flex items-start gap-2.5 rounded-xl border p-3'
      }
    >
      <AlertTriangle
        className={
          tone === 'critical'
            ? 'text-critical mt-0.5 size-4 shrink-0'
            : 'text-warning mt-0.5 size-4 shrink-0'
        }
      />
      <div>
        <p className="text-ink-secondary text-[12.5px] font-medium">{text}</p>
        {detail ? <p className="text-muted mt-0.5 text-[11.5px]">{detail}</p> : null}
      </div>
    </div>
  )
}
