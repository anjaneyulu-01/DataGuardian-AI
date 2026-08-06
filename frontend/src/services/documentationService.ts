/**
 * Documentation generation.
 *
 * There is no dedicated docs endpoint yet, but the agent already handles the
 * `generate_documentation` intent — so this routes through
 * `POST /api/v1/agent/analyze` with a targeted prompt rather than inventing a
 * second AI path. When a purpose-built endpoint lands, only this file changes.
 */

import { analyzeQuestion } from './agentService'
import { demoOnly, type Sourced } from './fallback'
import { docTemplates } from '@/data/mockData'
import type { DocTemplate } from '@/types/domain'

export type DocKind =
  | 'readme'
  | 'dataset'
  | 'glossary'
  | 'sql'
  | 'dictionary'

export interface DocRequest {
  kind: DocKind
  /** Asset the documentation is about. Optional for the glossary. */
  assetName?: string
  /** SQL to explain — only used by the `sql` kind. */
  sql?: string
}

export interface GeneratedDoc {
  kind: DocKind
  title: string
  /** Markdown body, ready to preview or download. */
  content: string
  assetName: string | null
}

/** Prompt per document kind. Kept here so wording is reviewable in one place. */
const PROMPTS: Record<DocKind, (target: string, extra?: string) => string> = {
  readme: (target) =>
    `Generate a README for the dataset ${target}. Cover its purpose, grain, ` +
    `refresh cadence, and any caveats a consumer must know.`,
  dataset: (target) =>
    `Generate full dataset documentation for ${target}: what it contains, who ` +
    `uses it, how it is produced, and its known limitations.`,
  glossary: (target) =>
    `Generate business glossary entries for the key terms in ${target}. ` +
    `Define each term in plain language a non-engineer can act on.`,
  sql: (target, sql) =>
    `Explain what this SQL does, step by step, and flag any correctness risks:\n\n` +
    `${sql ?? `-- transformation for ${target}`}`,
  dictionary: (target) =>
    `Generate a data dictionary for ${target} as a markdown table with ` +
    `columns: Column, Type, Description.`,
}

const TITLES: Record<DocKind, string> = {
  readme: 'README',
  dataset: 'Dataset Documentation',
  glossary: 'Business Glossary',
  sql: 'SQL Explanation',
  dictionary: 'Data Dictionary',
}

export async function generateDocument(
  request: DocRequest,
): Promise<Sourced<GeneratedDoc>> {
  const target = request.assetName?.trim() || 'the catalogue'
  const prompt = PROMPTS[request.kind](target, request.sql)

  const { data, source, reason } = await analyzeQuestion(prompt)

  // The agent returns an explanation, not a document. Its summary IS the
  // drafted prose; the recommendations become a review checklist.
  const body =
    data.raw?.summary ??
    demoTemplate(request.kind)?.preview ??
    'No documentation could be generated.'

  const checklist = data.raw?.next_steps ?? []
  const content = checklist.length
    ? `${body}\n\n---\n\n**Review before publishing**\n\n${checklist
        .map((step) => `- ${step}`)
        .join('\n')}`
    : body

  return {
    data: {
      kind: request.kind,
      title: TITLES[request.kind],
      content,
      assetName: request.assetName ?? null,
    },
    source,
    reason,
  }
}

/** Template metadata for the generator cards. */
export async function fetchDocTemplates(): Promise<Sourced<DocTemplate[]>> {
  return demoOnly(
    ALL_TEMPLATES,
    'Template definitions are static; generated content comes from the live agent.',
  )
}

function demoTemplate(kind: DocKind): DocTemplate | undefined {
  return ALL_TEMPLATES.find((template) => template.id === kind)
}

/** The five generators, extending the four already in demo data. */
const ALL_TEMPLATES: DocTemplate[] = [
  { ...docTemplates[0], id: 'readme' },
  {
    ...docTemplates[1],
    id: 'dictionary',
  },
  {
    id: 'dataset',
    title: 'Dataset Documentation',
    description: 'Full documentation: contents, producers, consumers, limitations.',
    icon: 'file-text',
    preview:
      '## fct_payments\n\n**Contents** — One row per settled payment.\n\n' +
      '**Produced by** — dbt job `finance_hourly`, running at :15 past each hour.\n\n' +
      '**Consumed by** — 17 downstream assets, including the certified\n' +
      '`fct_revenue_daily` and the executive KPI dashboard.\n\n' +
      '**Limitations** — Refunds appear as negative amounts rather than\n' +
      'separate rows; rows before 2024-03 have no `processor_fee`.',
  },
  {
    id: 'glossary',
    title: 'Business Glossary',
    description: 'Plain-language definitions of the business terms in an asset.',
    icon: 'book-marked',
    preview:
      '**Settled Payment** — A payment the processor has confirmed and for\n' +
      'which funds have moved. Distinct from an *authorised* payment, which\n' +
      'is only a hold.\n\n' +
      '**Minor Units** — Currency amounts stored as integers in the smallest\n' +
      'denomination (cents for USD). Divide by 100 before display.\n\n' +
      '**Chargeback** — A forced reversal initiated by the cardholder\'s bank.\n' +
      'Appears as a negative amount with `reason_code` populated.',
  },
  { ...docTemplates[3], id: 'sql' },
]

/** Trigger a browser download of the generated markdown. */
export function downloadDocument(doc: GeneratedDoc): void {
  const slug = (doc.assetName ?? 'dataguardian').replace(/[^a-z0-9]+/gi, '-')
  const blob = new Blob([doc.content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${slug}-${doc.kind}.md`
  anchor.click()

  // Release the object URL, or the blob leaks for the page's lifetime.
  URL.revokeObjectURL(url)
}
