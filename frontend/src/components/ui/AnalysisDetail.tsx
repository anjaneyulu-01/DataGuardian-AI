import { Check, Download, FileText, ShieldAlert, Workflow } from 'lucide-react'
import { useState } from 'react'

import { BusinessImpact } from './BusinessImpact'
import { Card } from './Card'
import { EvidenceCompleteness } from './EvidenceCompleteness'
import { ExecutionTimeline } from './ExecutionTimeline'
import { RiskExplainer } from './RiskExplainer'
import type { DataSource } from '@/services'
import type { ApiAgentResult } from '@/types/api'
import { cn } from '@/utils'
import {
  buildExecutiveReport,
  downloadMarkdown,
  reportFilename,
} from '@/utils/executiveReport'

interface AnalysisDetailProps {
  result: ApiAgentResult
  source: DataSource
}

type Tab = 'risk' | 'pipeline' | 'impact'

const TABS: { id: Tab; label: string; icon: typeof ShieldAlert }[] = [
  { id: 'risk', label: 'Why this score', icon: ShieldAlert },
  { id: 'pipeline', label: 'Execution', icon: Workflow },
  { id: 'impact', label: 'Impact', icon: FileText },
]

/**
 * The evidence panel shown under every analysis.
 *
 * Always visible — it is not a developer affordance. The execution pipeline
 * and the score arithmetic are the two things that distinguish this from a
 * chatbot, so hiding either behind a toggle loses the argument to anyone who
 * does not go looking.
 *
 * Tabbed rather than stacked because all three sections are long, and a
 * reader who wants the pipeline should not have to scroll past the rule
 * breakdown to reach it. "Why this score" leads: it is the claim the rest of
 * the product rests on.
 */
export function AnalysisDetail({ result, source }: AnalysisDetailProps) {
  const [tab, setTab] = useState<Tab>('risk')
  const [copied, setCopied] = useState(false)

  const exportReport = () => {
    const markdown = buildExecutiveReport(result, {
      source: source === 'demo' ? 'demo' : 'live',
    })
    downloadMarkdown(reportFilename(result), markdown)
  }

  const copyReport = async () => {
    const markdown = buildExecutiveReport(result, {
      source: source === 'demo' ? 'demo' : 'live',
    })
    try {
      await navigator.clipboard.writeText(markdown)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard is permission-gated and blocked in some embeds. Falling
      // back to the download keeps the action honest rather than silently
      // doing nothing.
      downloadMarkdown(reportFilename(result), markdown)
    }
  }

  return (
    <Card className="mt-4 overflow-hidden">
      <div className="border-line flex flex-wrap items-center gap-1 border-b px-2 py-2">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            aria-current={tab === id}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12.5px] font-medium transition-colors',
              tab === id
                ? 'bg-brand/12 text-ink'
                : 'text-muted hover:text-ink hover:bg-raised',
            )}
          >
            <Icon className="size-3.5" />
            {label}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-1">
          <button
            type="button"
            onClick={copyReport}
            className="text-muted hover:text-ink hover:bg-raised inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12px] font-medium transition-colors"
          >
            {copied ? (
              <Check className="text-positive size-3.5" />
            ) : (
              <FileText className="size-3.5" />
            )}
            {copied ? 'Copied' : 'Copy report'}
          </button>
          <button
            type="button"
            onClick={exportReport}
            title="Download this assessment as Markdown"
            className="text-muted hover:text-ink hover:bg-raised inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12px] font-medium transition-colors"
          >
            <Download className="size-3.5" />
            Markdown
          </button>
        </div>
      </div>

      <div className="p-4">
        {tab === 'risk' ? (
          <RiskExplainer
            findings={result.findings}
            riskScore={result.risk_score}
            riskLevel={result.risk_level}
          />
        ) : null}

        {tab === 'pipeline' ? (
          <div className="space-y-4">
            <ExecutionTimeline
              trace={result.trace}
              durationMs={result.duration_ms}
              provider={result.llm_provider}
            />
            <EvidenceCompleteness trace={result.trace} degraded={result.degraded} />
          </div>
        ) : null}

        {tab === 'impact' ? <BusinessImpact result={result} /> : null}
      </div>
    </Card>
  )
}
