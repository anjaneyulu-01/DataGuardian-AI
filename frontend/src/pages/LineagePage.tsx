import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
} from '@xyflow/react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Boxes,
  BrainCircuit,
  Database,
  LayoutDashboard,
  Sparkles,
  UserX,
  Workflow,
  X,
  type LucideIcon,
} from 'lucide-react'
import { memo, useMemo, useState } from 'react'

import {
  LoadingSkeleton,
  PageHeader,
  RiskBadge,
  SearchBar,
  SourceTag,
} from '@/components/ui'
import { useGovernanceAssets, useLineage } from '@/hooks/queries'
import type { LineageNodeData } from '@/types/domain'
import { cn } from '@/utils'
import { SEVERITY } from '@/utils/severity'

/** Icon and accent per node kind — the four the graph distinguishes. */
const KIND: Record<
  LineageNodeData['kind'],
  { icon: LucideIcon; label: string; accent: string }
> = {
  dataset: { icon: Database, label: 'Dataset', accent: 'text-brand-strong' },
  pipeline: { icon: Workflow, label: 'Pipeline', accent: 'text-accent' },
  dashboard: { icon: LayoutDashboard, label: 'Dashboard', accent: 'text-positive' },
  model: { icon: BrainCircuit, label: 'ML Model', accent: 'text-warning' },
}

type LineageFlowNode = Node<LineageNodeData>

/**
 * Custom React Flow node, styled as a product card.
 *
 * Memoised: React Flow re-renders every node on pan and zoom, so an
 * unmemoised node component makes a fifty-node graph stutter.
 */
const AssetNode = memo(function AssetNode({ data, selected }: NodeProps<LineageFlowNode>) {
  const kind = KIND[data.kind] ?? KIND.dataset
  const Icon = kind.icon
  const severity = SEVERITY[data.severity]

  return (
    <div
      className={cn(
        'card w-56 px-3.5 py-3 transition-all',
        selected && 'shadow-glow border-brand/50',
        data.isRoot && 'border-brand/40 ring-brand/20 ring-2',
        data.dimmed && 'opacity-25',
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-line-strong !border-0" />

      <div className="flex items-center gap-2.5">
        <span
          className={cn(
            'border-line bg-raised grid size-7 shrink-0 place-items-center rounded-md border',
            kind.accent,
          )}
        >
          <Icon className="size-3.5" />
        </span>
        <div className="min-w-0">
          <p className="text-ink truncate text-[12.5px] font-semibold">{data.name}</p>
          <p className="text-faint text-[10.5px]">
            {kind.label} · {data.platform}
          </p>
        </div>
        <span className={cn('ml-auto size-2 shrink-0 rounded-full', severity.dot)} />
      </div>

      {!data.owner ? (
        <p className="text-critical mt-2 flex items-center gap-1 text-[10.5px] font-medium">
          <UserX className="size-3" /> No owner
        </p>
      ) : null}

      <Handle type="source" position={Position.Right} className="!bg-line-strong !border-0" />
    </div>
  )
})

const nodeTypes: NodeTypes = { asset: AssetNode }

export function LineagePage() {
  const [selectedUrn, setSelectedUrn] = useState<string | null>(null)
  const [inspected, setInspected] = useState<LineageNodeData | null>(null)
  const [search, setSearch] = useState('')

  // The asset picker is backed by the same catalogue the Governance page uses.
  const catalogue = useGovernanceAssets({ search, count: 25 })
  const lineage = useLineage(selectedUrn)

  const graph = lineage.data?.data

  /**
   * Nodes and edges directly connected to the inspected node.
   *
   * Selecting a node in a dense graph is useless without this: the point of
   * clicking `fct_payments` is to see what it touches, and dimming everything
   * else is what makes that legible.
   */
  const connected = useMemo(() => {
    if (!inspected || !graph) return null
    const nodeIds = new Set<string>([inspected.urn])
    const edgeIds = new Set<string>()

    for (const edge of graph.edges) {
      if (edge.source === inspected.urn || edge.target === inspected.urn) {
        edgeIds.add(edge.id)
        nodeIds.add(edge.source)
        nodeIds.add(edge.target)
      }
    }
    return { nodeIds, edgeIds }
  }, [inspected, graph])

  const nodes: LineageFlowNode[] = useMemo(
    () =>
      (graph?.nodes ?? []).map((node) => ({
        id: node.id,
        type: 'asset',
        position: node.position,
        data: {
          ...node.data,
          // Dim anything outside the selection, so the connected subgraph
          // reads at a glance.
          dimmed: connected ? !connected.nodeIds.has(node.id) : false,
        },
      })),
    [graph, connected],
  )

  const edges: Edge[] = useMemo(
    () =>
      (graph?.edges ?? []).map((edge) => {
        const isConnected = connected ? connected.edgeIds.has(edge.id) : true
        return {
          ...edge,
          // Only animate the highlighted path: animating every edge in a
          // large graph is a constant repaint for no information gain.
          animated: isConnected,
          style: {
            opacity: isConnected ? 1 : 0.18,
            stroke: isConnected && connected ? 'var(--t-brand)' : undefined,
            strokeWidth: isConnected && connected ? 2 : undefined,
          },
        }
      }),
    [graph, connected],
  )

  return (
    <div className="flex h-[calc(100vh-8.5rem)] min-h-[520px] flex-col">
      <PageHeader
        title="Lineage Explorer"
        description="Trace how data flows from sources to executive surfaces. Click any node to inspect it."
        action={
          lineage.data ? (
            <SourceTag source={lineage.data.source} reason={lineage.data.reason} />
          ) : null
        }
      />

      {/* Asset picker. */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Find an asset to trace…"
          className="min-w-56 flex-1 sm:max-w-xs"
        />
        <div className="flex flex-wrap gap-1.5">
          {(catalogue.data?.data.assets ?? []).slice(0, 5).map((asset) => (
            <button
              key={asset.urn}
              type="button"
              onClick={() => {
                setSelectedUrn(asset.urn)
                setInspected(null)
              }}
              className={cn(
                'rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors',
                selectedUrn === asset.urn
                  ? 'border-brand/40 bg-brand/12 text-ink'
                  : 'border-line bg-surface text-muted hover:text-ink',
              )}
            >
              {asset.name}
            </button>
          ))}
        </div>

        {/* Legend — four node types. */}
        <div className="text-faint ml-auto hidden items-center gap-3 text-[11px] lg:flex">
          {Object.entries(KIND).map(([key, { icon: Icon, label, accent }]) => (
            <span key={key} className="inline-flex items-center gap-1">
              <Icon className={cn('size-3', accent)} />
              {label}
            </span>
          ))}
        </div>
      </div>

      <div className="card relative min-h-0 flex-1 overflow-hidden">
        {lineage.isPending ? (
          <div className="p-6">
            <LoadingSkeleton count={5} />
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_event, node) => setInspected(node.data)}
            onPaneClick={() => setInspected(null)}
            fitView
            proOptions={{ hideAttribution: true }}
            minZoom={0.3}
            maxZoom={1.6}
          >
            <Background color="var(--t-line)" gap={24} size={1.5} />
            <Controls showInteractive={false} />
            <MiniMap
              pannable
              nodeColor={(node) => SEVERITY[(node.data as LineageNodeData).severity].hex}
              maskColor="transparent"
            />
          </ReactFlow>
        )}

        {/* Inspector drawer. */}
        <AnimatePresence>
          {inspected ? (
            <motion.aside
              key={inspected.urn}
              initial={{ x: 380, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 380, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 380, damping: 34 }}
              className="border-line bg-surface/95 absolute inset-y-0 right-0 z-10 w-full max-w-sm overflow-y-auto border-l p-5 backdrop-blur-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-ink text-[15px] font-semibold">{inspected.name}</p>
                  <p className="text-faint mt-0.5 text-[11.5px]">
                    {KIND[inspected.kind]?.label ?? 'Asset'} · {inspected.platform}
                  </p>
                </div>
                <button
                  type="button"
                  aria-label="Close inspector"
                  onClick={() => setInspected(null)}
                  className="text-muted hover:bg-raised hover:text-ink grid size-7 shrink-0 place-items-center rounded-lg transition-colors"
                >
                  <X className="size-4" />
                </button>
              </div>

              <dl className="mt-5 space-y-4">
                <Field label="Risk">
                  <RiskBadge severity={inspected.severity} />
                </Field>

                <Field label="Owner">
                  {inspected.owner ? (
                    <span className="text-ink-secondary text-[13px]">{inspected.owner}</span>
                  ) : (
                    <span className="text-critical flex items-center gap-1.5 text-[13px] font-medium">
                      <UserX className="size-3.5" /> Unassigned
                    </span>
                  )}
                </Field>

                <Field label="Description">
                  {inspected.description ? (
                    <p className="text-ink-secondary text-[13px] leading-relaxed">
                      {inspected.description}
                    </p>
                  ) : (
                    <p className="text-critical text-[12.5px] font-medium">
                      Missing — flagged by the documentation rule.
                    </p>
                  )}
                </Field>

                <Field label="Tags">
                  {inspected.tags.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {inspected.tags.map((tag) => (
                        <span
                          key={tag}
                          className="border-line bg-raised text-muted rounded-full border px-2 py-0.5 text-[11px] font-medium"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-faint text-[12.5px]">None</span>
                  )}
                </Field>

                <Field
                  label={
                    <span className="text-brand-strong flex items-center gap-1">
                      <Sparkles className="size-3" /> AI Summary
                    </span>
                  }
                >
                  <div className="border-brand/25 bg-brand/8 rounded-xl border p-3">
                    <p className="text-ink-secondary text-[12.5px] leading-relaxed">
                      {inspected.aiSummary}
                    </p>
                  </div>
                </Field>

                <Field label="Lineage">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedUrn(inspected.urn)
                      setInspected(null)
                    }}
                    className="border-line bg-raised text-ink-secondary hover:border-brand/40 hover:text-ink inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors"
                  >
                    <Boxes className="size-3.5" /> Trace from this asset
                  </button>
                </Field>

                <Field label="URN">
                  <code className="text-faint block text-[10.5px] leading-relaxed break-all">
                    {inspected.urn}
                  </code>
                </Field>
              </dl>
            </motion.aside>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div>
      <dt className="text-faint mb-1.5 text-[10.5px] font-semibold tracking-widest uppercase">
        {label}
      </dt>
      <dd>{children}</dd>
    </div>
  )
}
