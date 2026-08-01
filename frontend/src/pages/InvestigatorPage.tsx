import {
  ClockAlert,
  Copy,
  ScanSearch,
  ShieldAlert,
  Unlink,
  UserX,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router'

import {
  AIResponse,
  Card,
  LoadingState,
  PageHeader,
  PromptInput,
  SectionHeader,
} from '@/components/ui'
import {
  aiAnswers,
  exampleQuestions,
  fallbackAnswer,
  suggestedActions,
} from '@/data/mockData'
import type { AIAnswer } from '@/types/domain'

const ACTION_ICONS: Record<string, LucideIcon> = {
  'user-x': UserX,
  'scan-search': ScanSearch,
  'shield-alert': ShieldAlert,
  unlink: Unlink,
  'clock-alert': ClockAlert,
  copy: Copy,
}

/** How long the fake "thinking" phase lasts. Real agent latency replaces it. */
const THINK_MS = 1400

interface Exchange {
  id: number
  answer: AIAnswer
}

/**
 * The product's core surface: ask → agent investigates → structured answer.
 *
 * DEMO MODE: answers come from `mockData.aiAnswers`, matched by keyword.
 * The LangGraph agent endpoint (Phase 4) replaces `resolveAnswer` +
 * `THINK_MS` with a real API call; everything else stays.
 */
export function InvestigatorPage() {
  const location = useLocation()
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [thinking, setThinking] = useState(false)
  const nextId = useRef(1)
  const bottomRef = useRef<HTMLDivElement>(null)
  const firedForState = useRef<string | null>(null)

  const ask = (prompt: string) => {
    if (thinking) return
    setThinking(true)

    window.setTimeout(() => {
      const answer = resolveAnswer(prompt)
      setExchanges((current) => [
        ...current,
        { id: nextId.current++, answer: { ...answer, question: prompt } },
      ])
      setThinking(false)
    }, THINK_MS)
  }

  // A prompt handed over from another page (Overview quick actions).
  useEffect(() => {
    const handed = (location.state as { prompt?: string } | null)?.prompt
    if (handed && firedForState.current !== handed) {
      firedForState.current = handed
      ask(handed)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [exchanges.length, thinking])

  const hasConversation = exchanges.length > 0 || thinking

  return (
    <div className="mx-auto max-w-3xl">
      {!hasConversation ? (
        <div className="pt-8 pb-4 text-center sm:pt-16">
          <PageHeaderHero />
        </div>
      ) : (
        <PageHeader
          title="AI Investigator"
          description="Every answer is grounded in catalogue metadata: reasoning, risk, evidence, recommendation."
        />
      )}

      <PromptInput
        size={hasConversation ? 'default' : 'hero'}
        onSubmit={ask}
        disabled={thinking}
        examples={hasConversation ? [] : exampleQuestions}
      />

      {/* Suggested actions — landing state only. */}
      {!hasConversation ? (
        <div className="mt-10">
          <SectionHeader title="Suggested Investigations" />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {suggestedActions.map((action) => {
              const Icon = ACTION_ICONS[action.icon] ?? ScanSearch
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

      {/* Conversation. */}
      <div className="mt-6 space-y-5">
        {exchanges.map((exchange) => (
          <AIResponse
            key={exchange.id}
            answer={exchange.answer}
            onAction={(action) => ask(action)}
          />
        ))}
        {thinking ? <LoadingState variant="thinking" /> : null}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function PageHeaderHero() {
  return (
    <>
      <h1 className="text-ink text-2xl font-semibold tracking-tight sm:text-3xl">
        Ask DataGuardian
      </h1>
      <p className="text-muted mx-auto mt-2 mb-8 max-w-md text-sm leading-relaxed">
        Your autonomous metadata governance engineer. Investigations are
        grounded in live DataHub metadata — never guesses.
      </p>
    </>
  )
}

/**
 * Keyword-match a prompt to a canned demo answer.
 * Replaced wholesale by the agent API in Phase 4.
 */
function resolveAnswer(prompt: string): AIAnswer {
  const lowered = prompt.toLowerCase()

  if (lowered.includes('owner')) return byId('missing-owners')
  if (lowered.includes('risk')) return byId('highest-risk')
  if (lowered.includes('impact') || lowered.includes('downstream'))
    return byId('downstream-impact')
  if (lowered.includes('document') || lowered.includes('docs'))
    return byId('generate-docs')
  if (lowered.includes('analyze') || lowered.includes('health'))
    return byId('highest-risk')
  if (lowered.includes('pii')) return byId('missing-owners')

  return fallbackAnswer
}

function byId(id: string): AIAnswer {
  return aiAnswers.find((answer) => answer.id === id) ?? fallbackAnswer
}
