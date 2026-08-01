import {
  BookOpen,
  Briefcase,
  Check,
  Code,
  Copy,
  Sparkles,
  TableProperties,
  type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'

import { Card, LoadingState, PageHeader, SectionHeader } from '@/components/ui'
import { docTemplates } from '@/data/mockData'
import type { DocTemplate } from '@/types/domain'
import { cn } from '@/utils'

const TEMPLATE_ICONS: Record<string, LucideIcon> = {
  'book-open': BookOpen,
  'table-properties': TableProperties,
  briefcase: Briefcase,
  code: Code,
}

/** Simulated generation delay; replaced by the Gemini endpoint in Phase 4. */
const GENERATE_MS = 1100

/**
 * AI documentation studio: pick a generator, preview the draft, copy it out.
 * The write-back-to-DataHub action lands with the agent phase.
 */
export function DocumentationPage() {
  const [active, setActive] = useState<DocTemplate>(docTemplates[0])
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState(false)
  const [copied, setCopied] = useState(false)

  const generate = (template: DocTemplate) => {
    setActive(template)
    setGenerated(false)
    setGenerating(true)
    window.setTimeout(() => {
      setGenerating(false)
      setGenerated(true)
    }, GENERATE_MS)
  }

  const copy = async () => {
    await navigator.clipboard.writeText(active.preview)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div>
      <PageHeader
        title="Documentation"
        description="AI-drafted documentation for undocumented assets — always reviewed by a human before it is written back to DataHub."
      />

      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        {/* Generators. */}
        <div>
          <SectionHeader title="Generators" />
          <div className="space-y-3">
            {docTemplates.map((template) => {
              const Icon = TEMPLATE_ICONS[template.icon] ?? BookOpen
              const isActive = active.id === template.id
              return (
                <Card
                  key={template.id}
                  interactive
                  onClick={() => generate(template)}
                  className={cn(
                    'flex items-start gap-3 p-4',
                    isActive && 'border-brand/40 shadow-glow',
                  )}
                >
                  <span
                    className={cn(
                      'grid size-9 shrink-0 place-items-center rounded-lg border transition-colors',
                      isActive
                        ? 'border-brand/30 bg-brand/10 text-brand-strong'
                        : 'border-line bg-raised text-muted',
                    )}
                  >
                    <Icon className="size-4" strokeWidth={2} />
                  </span>
                  <div>
                    <p className="text-ink text-[13px] font-semibold">{template.title}</p>
                    <p className="text-muted mt-0.5 text-[12px] leading-snug">
                      {template.description}
                    </p>
                  </div>
                </Card>
              )
            })}
          </div>
        </div>

        {/* Preview panel. */}
        <div>
          <SectionHeader
            title="Preview"
            description="Target: finance.fct_payments (Snowflake)"
            action={
              generated ? (
                <button
                  type="button"
                  onClick={() => void copy()}
                  className="border-line bg-surface text-muted hover:text-ink flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="text-positive size-3.5" /> Copied
                    </>
                  ) : (
                    <>
                      <Copy className="size-3.5" /> Copy
                    </>
                  )}
                </button>
              ) : null
            }
          />

          <Card className="min-h-[420px] p-5">
            {generating ? (
              <div className="space-y-5">
                <LoadingState
                  variant="thinking"
                  label={`Drafting ${active.title.replace('Generate ', '').toLowerCase()}…`}
                  className="border-0 shadow-none"
                />
                <LoadingState rows={6} />
              </div>
            ) : generated ? (
              <div>
                <p className="text-brand-strong mb-3 flex items-center gap-1.5 text-[11px] font-semibold tracking-widest uppercase">
                  <Sparkles className="size-3" /> AI draft — review before publishing
                </p>
                <pre className="text-ink-secondary font-sans text-[13px] leading-relaxed whitespace-pre-wrap">
                  {active.preview}
                </pre>
              </div>
            ) : (
              <div className="grid h-full min-h-[360px] place-items-center">
                <div className="text-center">
                  <Sparkles className="text-faint mx-auto size-8" strokeWidth={1.5} />
                  <p className="text-ink mt-3 text-sm font-semibold">
                    Pick a generator to draft documentation
                  </p>
                  <p className="text-muted mx-auto mt-1 max-w-xs text-[12.5px]">
                    Drafts are grounded in the asset's schema, profiling
                    statistics, and lineage.
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
