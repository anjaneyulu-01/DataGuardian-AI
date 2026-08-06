import {
  BookMarked,
  BookOpen,
  Check,
  Code,
  Copy,
  Download,
  FileText,
  Sparkles,
  TableProperties,
  type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'

import {
  Card,
  LoadingSkeleton,
  LoadingState,
  PageHeader,
  SearchBar,
  SectionHeader,
  SourceTag,
} from '@/components/ui'
import { useDocTemplates, useGenerateDocument, useGovernanceAssets } from '@/hooks/queries'
import { downloadDocument, type DocKind } from '@/services'
import { cn } from '@/utils'

const ICONS: Record<string, LucideIcon> = {
  readme: BookOpen,
  dictionary: TableProperties,
  dataset: FileText,
  glossary: BookMarked,
  sql: Code,
}

export function DocumentationPage() {
  const [kind, setKind] = useState<DocKind>('readme')
  const [assetName, setAssetName] = useState('')
  const [search, setSearch] = useState('')
  const [sql, setSql] = useState('')
  const [copied, setCopied] = useState(false)

  const templates = useDocTemplates()
  const catalogue = useGovernanceAssets({ search, count: 25 })
  const generate = useGenerateDocument()

  const generated = generate.data?.data
  const activeTemplate = (templates.data?.data ?? []).find((t) => t.id === kind)

  const run = () => {
    generate.mutate({
      kind,
      assetName: assetName || undefined,
      sql: kind === 'sql' ? sql : undefined,
    })
  }

  const copy = async () => {
    if (!generated) return
    await navigator.clipboard.writeText(generated.content)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div>
      <PageHeader
        title="Documentation"
        description="AI-drafted documentation, grounded in DataHub metadata. Always reviewed before it is published."
        action={
          generate.data ? (
            <SourceTag source={generate.data.source} reason={generate.data.reason} />
          ) : null
        }
      />

      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        {/* Generators + target picker. */}
        <div>
          <SectionHeader title="Generators" />
          {templates.isPending ? (
            <LoadingSkeleton variant="card" count={5} />
          ) : (
            <div className="space-y-2.5">
              {(templates.data?.data ?? []).map((template) => {
                const Icon = ICONS[template.id] ?? BookOpen
                const isActive = kind === template.id
                return (
                  <Card
                    key={template.id}
                    interactive
                    onClick={() => setKind(template.id as DocKind)}
                    className={cn(
                      'flex items-start gap-3 p-3.5',
                      isActive && 'border-brand/40 shadow-glow',
                    )}
                  >
                    <span
                      className={cn(
                        'grid size-8 shrink-0 place-items-center rounded-lg border transition-colors',
                        isActive
                          ? 'border-brand/30 bg-brand/10 text-brand-strong'
                          : 'border-line bg-raised text-muted',
                      )}
                    >
                      <Icon className="size-4" strokeWidth={2} />
                    </span>
                    <div>
                      <p className="text-ink text-[13px] font-semibold">{template.title}</p>
                      <p className="text-muted mt-0.5 text-[11.5px] leading-snug">
                        {template.description}
                      </p>
                    </div>
                  </Card>
                )
              })}
            </div>
          )}

          {/* Target asset. */}
          <div className="mt-5">
            <SectionHeader title="Target" />
            <SearchBar
              value={search}
              onChange={setSearch}
              placeholder="Find a dataset…"
              className="mb-2.5"
            />
            <div className="flex flex-wrap gap-1.5">
              {(catalogue.data?.data.assets ?? []).slice(0, 6).map((asset) => (
                <button
                  key={asset.urn}
                  type="button"
                  onClick={() => setAssetName(asset.name)}
                  className={cn(
                    'rounded-lg border px-2.5 py-1.5 text-[11.5px] font-medium transition-colors',
                    assetName === asset.name
                      ? 'border-brand/40 bg-brand/12 text-ink'
                      : 'border-line bg-surface text-muted hover:text-ink',
                  )}
                >
                  {asset.name}
                </button>
              ))}
            </div>

            {kind === 'sql' ? (
              <textarea
                value={sql}
                onChange={(event) => setSql(event.target.value)}
                placeholder="Paste the SQL to explain…"
                rows={5}
                className="card text-ink placeholder:text-faint focus:shadow-glow mt-3 w-full resize-y px-3 py-2.5 font-mono text-[12px] outline-none transition-shadow"
              />
            ) : null}

            <button
              type="button"
              onClick={run}
              disabled={generate.isPending}
              className="bg-brand hover:bg-brand-strong shadow-glow mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-lg px-4 py-2.5 text-[13px] font-medium text-white transition-colors disabled:opacity-60"
            >
              <Sparkles className="size-4" />
              {generate.isPending ? 'Generating…' : 'Generate'}
            </button>
          </div>
        </div>

        {/* Preview. */}
        <div>
          <SectionHeader
            title="Preview"
            description={
              assetName ? `Target: ${assetName}` : 'Pick a target asset, or generate for the catalogue.'
            }
            action={
              generated ? (
                <div className="flex gap-2">
                  <PanelButton onClick={() => void copy()}>
                    {copied ? (
                      <>
                        <Check className="text-positive size-3.5" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="size-3.5" /> Copy
                      </>
                    )}
                  </PanelButton>
                  <PanelButton onClick={() => downloadDocument(generated)}>
                    <Download className="size-3.5" /> Download
                  </PanelButton>
                </div>
              ) : null
            }
          />

          <Card className="min-h-[440px] p-5">
            {generate.isPending ? (
              <div className="space-y-5">
                <LoadingState
                  variant="thinking"
                  label={`Drafting ${activeTemplate?.title.toLowerCase() ?? 'documentation'}…`}
                  className="border-0 shadow-none"
                />
                <LoadingSkeleton count={7} />
              </div>
            ) : generated ? (
              <div>
                <p className="text-brand-strong mb-3 flex items-center gap-1.5 text-[11px] font-semibold tracking-widest uppercase">
                  <Sparkles className="size-3" /> AI draft — review before publishing
                </p>
                <pre className="text-ink-secondary font-sans text-[13px] leading-relaxed whitespace-pre-wrap">
                  {generated.content}
                </pre>
              </div>
            ) : generate.isError ? (
              <div className="grid h-full min-h-[380px] place-items-center text-center">
                <div>
                  <p className="text-ink text-sm font-semibold">Generation failed</p>
                  <p className="text-muted mx-auto mt-1 max-w-xs text-[12.5px]">
                    {generate.error.message}
                  </p>
                </div>
              </div>
            ) : (
              // Idle: show the template's example so the panel is never blank.
              <div>
                <p className="text-faint mb-3 text-[11px] font-semibold tracking-widest uppercase">
                  Example output
                </p>
                <pre className="text-muted font-sans text-[13px] leading-relaxed whitespace-pre-wrap">
                  {activeTemplate?.preview ?? 'Choose a generator to begin.'}
                </pre>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}

function PanelButton({
  onClick,
  children,
}: {
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="border-line bg-surface text-muted hover:text-ink flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors"
    >
      {children}
    </button>
  )
}
