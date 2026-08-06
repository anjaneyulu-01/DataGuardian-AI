import { motion } from 'framer-motion'
import {
  Boxes,
  Brain,
  Database,
  GitBranch,
  Layers,
  Network,
  ScrollText,
  ShieldAlert,
  Sparkles,
  Users,
  Workflow,
  Zap,
  type LucideIcon,
} from 'lucide-react'

import { Card, PageHeader, SectionHeader } from '@/components/ui'
import { cn } from '@/utils'

/**
 * How the system is built.
 *
 * Exists because the most important thing about this product is invisible in
 * the other screens: risk is computed deterministically and the LLM only
 * explains it. This page makes that architecture legible in about thirty
 * seconds.
 */
export function ArchitecturePage() {
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Architecture"
        description="How DataGuardian turns DataHub metadata into governance decisions — and why the numbers are reproducible."
      />

      {/* The load-bearing idea, stated first. */}
      <Card className="border-brand/25 from-brand/8 mb-6 bg-gradient-to-br to-transparent p-5">
        <div className="flex items-start gap-3.5">
          <span className="border-brand/30 bg-brand/10 text-brand-strong grid size-10 shrink-0 place-items-center rounded-xl border">
            <ShieldAlert className="size-5" />
          </span>
          <div>
            <p className="text-ink text-sm font-semibold">
              Deterministic rules decide what is wrong. The LLM only explains it.
            </p>
            <p className="text-muted mt-1.5 text-[13px] leading-relaxed">
              Risk scores come from a rule engine, so the same metadata always
              produces the same score and every point traces to a named rule. A
              language model that scored risk would invent violations that are
              not in the data — which is exactly the failure a governance tool
              cannot afford.
            </p>
          </div>
        </div>
      </Card>

      {/* System flow. */}
      <SectionHeader
        title="System Diagram"
        description="Request path from a question to a grounded answer."
      />
      <Card className="mb-8 overflow-x-auto p-5">
        <div className="flex min-w-[720px] items-stretch gap-2">
          {SYSTEM_FLOW.map((layer, index) => (
            <motion.div
              key={layer.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08, duration: 0.3 }}
              className="flex flex-1 items-center gap-2"
            >
              <div
                className={cn(
                  'flex-1 rounded-xl border p-3.5 transition-shadow hover:shadow-pop',
                  layer.tone,
                )}
              >
                <layer.icon className="size-4" />
                <p className="text-ink mt-2 text-[12.5px] font-semibold">{layer.title}</p>
                <p className="text-muted mt-1 text-[11px] leading-snug">{layer.detail}</p>
              </div>
              {index < SYSTEM_FLOW.length - 1 ? (
                <span className="text-faint shrink-0 text-lg">→</span>
              ) : null}
            </motion.div>
          ))}
        </div>
      </Card>

      {/* LangGraph workflow. */}
      <SectionHeader
        title="LangGraph Agent Workflow"
        description="Nodes execute conditionally — the planner decides which tools are needed."
      />
      <Card className="mb-8 p-5">
        <ol className="space-y-2.5">
          {AGENT_NODES.map((node, index) => (
            <motion.li
              key={node.name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05, duration: 0.28 }}
              className="flex items-start gap-3"
            >
              <span
                className={cn(
                  'grid size-8 shrink-0 place-items-center rounded-lg border',
                  node.tone,
                )}
              >
                <node.icon className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-2">
                  <p className="text-ink text-[13px] font-semibold">{node.name}</p>
                  <span className="text-faint text-[10px] font-medium tracking-wide uppercase">
                    {node.kind}
                  </span>
                </div>
                <p className="text-muted mt-0.5 text-[12px] leading-relaxed">
                  {node.detail}
                </p>
              </div>
            </motion.li>
          ))}
        </ol>

        <p className="border-line text-muted mt-4 border-t pt-3.5 text-[12px] leading-relaxed">
          <strong className="text-ink-secondary">Conditional routing.</strong> Asking
          &ldquo;find datasets without owners&rdquo; runs the dataset and owner tools
          and skips lineage and statistics entirely. Asking about downstream impact
          does the opposite. The execution trace on every answer shows which path
          was taken.
        </p>
      </Card>

      {/* Tool layer + DataHub. */}
      <div className="mb-8 grid gap-4 lg:grid-cols-2">
        <div>
          <SectionHeader
            title="Tool Layer"
            description="The agent's only route to metadata."
          />
          <Card className="p-5">
            <div className="space-y-3">
              {TOOLS.map((tool) => (
                <div key={tool.name} className="flex items-start gap-3">
                  <span className="border-accent/25 bg-accent/10 text-accent grid size-7 shrink-0 place-items-center rounded-md border">
                    <tool.icon className="size-3.5" />
                  </span>
                  <div>
                    <p className="text-ink text-[12.5px] font-semibold">{tool.name}</p>
                    <p className="text-muted text-[11.5px]">{tool.detail}</p>
                  </div>
                </div>
              ))}
            </div>
            <p className="border-line text-muted mt-4 border-t pt-3 text-[11.5px] leading-relaxed">
              The LLM never holds a DataHub client. It receives serialised JSON
              and nothing else — a structural boundary, not a convention.
            </p>
          </Card>
        </div>

        <div>
          <SectionHeader
            title="DataHub Integration"
            description="Six layers, each depending only on those below."
          />
          <Card className="p-5">
            <div className="space-y-2">
              {DATAHUB_LAYERS.map((layer) => (
                <div
                  key={layer.name}
                  className="border-line bg-raised/50 flex items-center gap-3 rounded-lg border px-3 py-2"
                >
                  <code className="text-brand-strong shrink-0 text-[11.5px] font-semibold">
                    {layer.name}
                  </code>
                  <span className="text-muted truncate text-[11.5px]">
                    {layer.detail}
                  </span>
                </div>
              ))}
            </div>
            <p className="border-line text-muted mt-4 border-t pt-3 text-[11.5px] leading-relaxed">
              Sparse metadata maps cleanly — an asset with no owner is the case
              the product exists to find, not an error.
            </p>
          </Card>
        </div>
      </div>

      {/* Stack. */}
      <SectionHeader title="Technology Stack" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STACK.map((group, index) => (
          <motion.div
            key={group.title}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.06, duration: 0.3 }}
          >
            <Card className="h-full p-4">
              <div className="flex items-center gap-2">
                <group.icon className="text-brand-strong size-4" />
                <p className="text-ink text-[12.5px] font-semibold">{group.title}</p>
              </div>
              <ul className="mt-3 space-y-1.5">
                {group.items.map((item) => (
                  <li key={item} className="text-muted text-[11.5px]">
                    {item}
                  </li>
                ))}
              </ul>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

const SYSTEM_FLOW: {
  title: string
  detail: string
  icon: LucideIcon
  tone: string
}[] = [
  {
    title: 'React Workspace',
    detail: 'TanStack Query, React Flow, Recharts',
    icon: Layers,
    tone: 'border-line bg-raised',
  },
  {
    title: 'FastAPI',
    detail: '13 typed endpoints, DI throughout',
    icon: Zap,
    tone: 'border-brand/25 bg-brand/8',
  },
  {
    title: 'LangGraph Agent',
    detail: 'Plans tools, gathers evidence',
    icon: Workflow,
    tone: 'border-brand/25 bg-brand/8',
  },
  {
    title: 'Rule Engine',
    detail: 'Deterministic risk scoring',
    icon: ShieldAlert,
    tone: 'border-positive/25 bg-positive/8',
  },
  {
    title: 'DataHub',
    detail: 'GraphQL metadata source',
    icon: Database,
    tone: 'border-accent/25 bg-accent/8',
  },
]

const AGENT_NODES: {
  name: string
  kind: string
  detail: string
  icon: LucideIcon
  tone: string
}[] = [
  {
    name: 'Planner',
    kind: 'Planning',
    detail:
      'Classifies the question into one of seven intents and selects only the tools that intent needs. Rules first; the LLM is consulted only on a genuine tie.',
    icon: Workflow,
    tone: 'border-brand/30 bg-brand/10 text-brand-strong',
  },
  {
    name: 'Tool Nodes',
    kind: 'Data gathering',
    detail:
      'Dataset, Owner, Lineage, and Statistics tools run conditionally against DataHub. A failure is contained: the graph continues on partial evidence and marks the run degraded.',
    icon: Boxes,
    tone: 'border-accent/30 bg-accent/10 text-accent',
  },
  {
    name: 'Risk Engine',
    kind: 'Deterministic',
    detail:
      'Six weighted rules — untagged PII (40), missing owner (30), missing docs (20), blast radius (20), deprecated-in-use (15), schema drift (15). No LLM. Reproducible and auditable.',
    icon: ShieldAlert,
    tone: 'border-positive/30 bg-positive/10 text-positive',
  },
  {
    name: 'Reasoning',
    kind: 'Generative',
    detail:
      'The LLM receives the verdict and the evidence that produced it, and writes the explanation. It is told the score, never asked to compute it.',
    icon: Brain,
    tone: 'border-warning/30 bg-warning/10 text-warning',
  },
  {
    name: 'Recommendation',
    kind: 'Generative',
    detail:
      'Proposes corrective actions bounded by the findings — it cannot recommend fixing something the rule engine never found.',
    icon: Sparkles,
    tone: 'border-warning/30 bg-warning/10 text-warning',
  },
]

const TOOLS: { name: string; detail: string; icon: LucideIcon }[] = [
  { name: 'DatasetTool', detail: 'list · get · search · undocumented', icon: Database },
  { name: 'OwnerTool', detail: 'list · for_dataset · has_owner', icon: Users },
  { name: 'LineageTool', detail: 'get · impact · downstream_count', icon: GitBranch },
  { name: 'StatisticsTool', detail: 'get · summary (prompt-sized)', icon: ScrollText },
  { name: 'DomainTool', detail: 'list · get · names', icon: Network },
]

const DATAHUB_LAYERS: { name: string; detail: string }[] = [
  { name: 'service.py', detail: 'Public interface; owns error semantics' },
  { name: 'cache.py', detail: 'TTL + LRU, single-flight, never caches failures' },
  { name: 'mapper.py', detail: 'GraphQL dicts → typed models' },
  { name: 'queries.py', detail: '12 documents, validated against v1.5.0.6' },
  { name: 'graphql.py', detail: 'Envelope validation and error translation' },
  { name: 'client.py', detail: 'Pooled HTTP, auth, jittered retries' },
]

const STACK: { title: string; items: string[]; icon: LucideIcon }[] = [
  {
    title: 'Frontend',
    items: ['React 19 + TypeScript', 'Vite 8', 'Tailwind CSS 4', 'TanStack Query'],
    icon: Layers,
  },
  {
    title: 'Backend',
    items: ['FastAPI · Python 3.12', 'Pydantic v2', 'SQLAlchemy 2', 'APScheduler'],
    icon: Zap,
  },
  {
    title: 'AI',
    items: ['LangGraph', 'Groq · Gemini', 'xAI · OpenAI · Claude', 'Automatic fail-over'],
    icon: Brain,
  },
  {
    title: 'Data',
    items: ['DataHub v1.5.0.6', 'GraphQL API', 'PostgreSQL', 'Docker Compose'],
    icon: Database,
  },
]
