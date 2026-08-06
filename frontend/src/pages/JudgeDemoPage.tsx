import { motion } from 'framer-motion'
import {
  CircleCheck,
  CircleDashed,
  Download,
  Play,
  RotateCcw,
  ShieldAlert,
  TriangleAlert,
  X,
} from 'lucide-react'
import { useRef, useState } from 'react'

import {
  AnalysisDetail,
  Card,
  PageHeader,
  RiskBadge,
  SectionHeader,
  SourceTag,
} from '@/components/ui'
import { analyzeQuestion, type DataSource } from '@/services'
import type { ApiAgentResult } from '@/types/api'
import type { Severity } from '@/types/domain'
import { cn } from '@/utils'
import {
  buildExecutiveReport,
  downloadMarkdown,
} from '@/utils/executiveReport'

/**
 * The scripted evaluation run.
 *
 * Four questions chosen to exercise *different* planner branches, because the
 * point being demonstrated is that the agent selects its own tools. If every
 * question ran the same nodes, the execution timeline would prove nothing.
 *
 * The `demonstrates` line is shown to the viewer so the intent of each step is
 * explicit rather than something they have to infer.
 */
const SCRIPT = [
  {
    question: 'Find datasets without owners',
    demonstrates:
      'Planner selects the owner tool and skips lineage and statistics — tool selection is per-question, not fixed.',
  },
  {
    question: 'Find untagged PII across all datasets',
    demonstrates:
      'The heaviest deterministic rule fires on schema field names, with no model involved in the decision.',
  },
  {
    question: 'Which datasets are highest risk?',
    demonstrates:
      'Lineage is now needed for blast radius, so the planner routes differently to step 1.',
  },
  {
    question: 'Create a governance report',
    demonstrates:
      'A different intent again — the report node runs and the LLM writes prose over the same deterministic findings.',
  },
] as const

type StepState = 'pending' | 'running' | 'done' | 'failed'

interface StepResult {
  state: StepState
  result: ApiAgentResult | null
  source: DataSource
  reason?: string
  error?: string
}

const INITIAL: StepResult[] = SCRIPT.map(() => ({
  state: 'pending',
  result: null,
  source: 'live',
}))

/**
 * Judge Demo — the whole product in one click, no typing.
 *
 * Exists because an evaluator has minutes, not an afternoon. It runs four real
 * `POST /api/v1/agent/analyze` calls in sequence and renders each result with
 * its full evidence panel.
 *
 * These are genuine agent runs, not a replay. If the backend is unreachable
 * the underlying service falls back to Demo Mode and every panel is tagged
 * accordingly — a scripted demo that silently fabricated results would
 * contradict the one claim this product makes.
 */
export function JudgeDemoPage() {
  const [steps, setSteps] = useState<StepResult[]>(INITIAL)
  const [running, setRunning] = useState(false)
  const [current, setCurrent] = useState(-1)
  const cancelled = useRef(false)

  const run = async () => {
    cancelled.current = false
    setRunning(true)
    setSteps(INITIAL)

    for (const [index, step] of SCRIPT.entries()) {
      if (cancelled.current) break

      setCurrent(index)
      setSteps((prev) =>
        prev.map((s, i) => (i === index ? { ...s, state: 'running' } : s)),
      )

      try {
        const outcome = await analyzeQuestion(step.question)
        if (cancelled.current) break
        setSteps((prev) =>
          prev.map((s, i) =>
            i === index
              ? {
                  state: 'done',
                  result: outcome.data.raw,
                  source: outcome.source,
                  reason: outcome.reason,
                }
              : s,
          ),
        )
      } catch (error) {
        if (cancelled.current) break
        setSteps((prev) =>
          prev.map((s, i) =>
            i === index
              ? {
                  ...s,
                  state: 'failed',
                  error: error instanceof Error ? error.message : String(error),
                }
              : s,
          ),
        )
      }
    }

    setCurrent(-1)
    setRunning(false)
  }

  const reset = () => {
    cancelled.current = true
    setSteps(INITIAL)
    setCurrent(-1)
    setRunning(false)
  }

  const completed = steps.filter((s) => s.state === 'done')
  const anyDemo = completed.some((s) => s.source === 'demo')
  const finished = !running && completed.length > 0

  /** One combined Markdown document covering every completed step. */
  const exportAll = () => {
    const sections = completed
      .filter((s) => s.result)
      .map((s) =>
        buildExecutiveReport(s.result as ApiAgentResult, {
          source: s.source === 'demo' ? 'demo' : 'live',
        }),
      )
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
    downloadMarkdown(
      `dataguardian-judge-demo-${stamp}.md`,
      sections.join('\n\n\\pagebreak\n\n'),
    )
  }

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="Judge Demo"
        description="Four real agent runs, in sequence, with no typing. Each exercises a different planner branch."
        action={
          finished ? (
            <button
              type="button"
              onClick={exportAll}
              className="border-line bg-surface text-muted hover:text-ink inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors"
            >
              <Download className="size-3.5" />
              Export all
            </button>
          ) : null
        }
      />

      {/* Control. */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={running ? reset : run}
            className={cn(
              'inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[13px] font-semibold transition-all',
              running
                ? 'border-line bg-raised text-ink-secondary hover:text-ink border'
                : 'bg-brand hover:bg-brand-strong shadow-glow text-white',
            )}
          >
            {running ? (
              <>
                <X className="size-4" />
                Stop
              </>
            ) : completed.length > 0 ? (
              <>
                <RotateCcw className="size-4" />
                Run again
              </>
            ) : (
              <>
                <Play className="size-4" />
                Run the demo
              </>
            )}
          </button>

          <div className="min-w-0 flex-1">
            <p className="text-ink text-[13px] font-medium">
              {running
                ? `Running step ${current + 1} of ${SCRIPT.length}…`
                : completed.length > 0
                  ? `${completed.length} of ${SCRIPT.length} analyses complete`
                  : 'Roughly 60–90 seconds. Every step is a live agent call.'}
            </p>
            <p className="text-muted mt-0.5 text-[12px]">
              Watch the execution pipeline change between steps — that is the
              planner choosing different tools.
            </p>
          </div>
        </div>

        {/* Step tracker. */}
        <ol className="mt-4 space-y-1.5">
          {SCRIPT.map((step, index) => {
            const state = steps[index].state
            return (
              <li key={step.question} className="flex items-start gap-2.5">
                <StepIcon state={state} />
                <div className="min-w-0 flex-1">
                  <p
                    className={cn(
                      'text-[12.5px] font-medium',
                      state === 'pending' ? 'text-faint' : 'text-ink',
                    )}
                  >
                    {step.question}
                  </p>
                  <p className="text-muted mt-0.5 text-[11.5px] leading-relaxed">
                    {step.demonstrates}
                  </p>
                </div>
              </li>
            )
          })}
        </ol>
      </Card>

      {anyDemo ? (
        <div className="border-warning/25 bg-warning/10 mt-4 flex items-start gap-2.5 rounded-xl border p-3">
          <TriangleAlert className="text-warning mt-0.5 size-4 shrink-0" />
          <div>
            <p className="text-ink-secondary text-[12.5px] font-medium">
              Some steps ran against demo data.
            </p>
            <p className="text-muted mt-0.5 text-[11.5px]">
              The backend was unreachable, so those answers come from the
              built-in catalogue rather than a live DataHub instance.
            </p>
          </div>
        </div>
      ) : null}

      {/* Results. */}
      <div className="mt-6 space-y-6">
        {steps.map((step, index) =>
          step.result ? (
            <motion.section
              key={SCRIPT[index].question}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
            >
              <SectionHeader
                title={`${index + 1}. ${SCRIPT[index].question}`}
                action={<SourceTag source={step.source} reason={step.reason} />}
              />

              <Card className="p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <ShieldAlert className="text-brand-strong size-4" />
                  <RiskBadge severity={step.result.risk_level as Severity} />
                  <span className="text-ink text-[13px] font-semibold tabular-nums">
                    {step.result.risk_score}/100
                  </span>
                  <span className="text-muted text-[12px]">
                    {step.result.findings.length} findings ·{' '}
                    {step.result.tools_used.length} tools ·{' '}
                    {Math.round(step.result.duration_ms)}ms
                  </span>
                </div>
                <p className="text-ink-secondary mt-2.5 text-[13px] leading-relaxed">
                  {step.result.summary}
                </p>
              </Card>

              <AnalysisDetail result={step.result} source={step.source} />
            </motion.section>
          ) : step.state === 'failed' ? (
            <div
              key={SCRIPT[index].question}
              className="border-critical/25 bg-critical/10 rounded-xl border p-3"
            >
              <p className="text-ink-secondary text-[12.5px] font-medium">
                Step {index + 1} failed: {SCRIPT[index].question}
              </p>
              <p className="text-muted mt-0.5 text-[11.5px]">{step.error}</p>
            </div>
          ) : null,
        )}
      </div>
    </div>
  )
}

function StepIcon({ state }: { state: StepState }) {
  if (state === 'done') {
    return <CircleCheck className="text-positive mt-0.5 size-4 shrink-0" />
  }
  if (state === 'failed') {
    return <X className="text-critical mt-0.5 size-4 shrink-0" />
  }
  if (state === 'running') {
    return (
      <CircleDashed className="text-brand-strong mt-0.5 size-4 shrink-0 animate-spin" />
    )
  }
  return <CircleDashed className="text-faint mt-0.5 size-4 shrink-0" />
}
