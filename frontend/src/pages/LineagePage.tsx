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
  BarChart3,
  Database,
  LayoutDashboard,
  Sparkles,
  UserX,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useMemo, useState } from 'react'

import { PageHeader, StatusBadge } from '@/components/ui'
import { lineageEdges, lineageNodes } from '@/data/mockData'
import type { LineageNodeData } from '@/types/domain'
import { cn } from '@/utils'
import { SEVERITY } from '@/utils/severity'

const KIND_ICON: Record<LineageNodeData['kind'], LucideIcon> = {
  source: Database,
  dataset: BarChart3,
  dashboard: LayoutDashboard,
}

type LineageFlowNode = Node<LineageNodeData>

/** Custom React Flow node styled as a product card. */
function AssetNode({ data, selected }: NodeProps<LineageFlowNode>) {
  const Icon = KIND_ICON[data.kind]
  const severity = SEVERITY[data.severity]

  return (
    <div
      className={cn(
        'card w-52 px-3.5 py-3 transition-shadow',
        selected && 'shadow-glow border-brand/50',
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-line-strong !border-0" />
      <div className="flex items-center gap-2.5">
        <span className="border-line bg-raised text-muted grid size-7 shrink-0 place-items-center rounded-md border">
          <Icon className="size-3.5" />
        </span>
        <div className="min-w-0">
          <p className="text-ink truncate text-[12.5px] font-semibold">{data.name}</p>
          <p className="text-faint text-[10.5px]">{data.platform}</p>
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
}

const nodeTypes: NodeTypes = { asset: AssetNode }

/**
 * Interactive lineage graph. Clicking a node opens the detail drawer with the
 * asset's governance state and an AI summary.
 *
 * DEMO MODE: graph ships from mockData; GET /api/v1/lineage/impact supplies
 * the same shape once a real URN is selected.
 */
export function LineagePage() {
  const [selected, setSelected] = useState<LineageNodeData | null>(null)

  const nodes: LineageFlowNode[] = useMemo(
    () =>
      lineageNodes.map((node) => ({
        id: node.id,
        type: 'asset',
        position: node.position,
        data: node.data,
      })),
    [],
  )

  const edges: Edge[] = useMemo(
    () =>
      lineageEdges.map((edge) => ({
        ...edge,
        animated: true,
      })),
    [],
  )

  return (
    <div className="flex h-[calc(100vh-8.5rem)] min-h-[480px] flex-col">
      <PageHeader
        title="Lineage Explorer"
        description="Trace how data flows from sources to executive surfaces. Click any node for its governance state."
      />

      <div className="card relative min-h-0 flex-1 overflow-hidden">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={(_event, node) => setSelected(node.data)}
          onPaneClick={() => setSelected(null)}
          fitView
          proOptions={{ hideAttribution: true }}
          minZoom={0.4}
          maxZoom={1.6}
        >
          <Background color="var(--t-line)" gap={24} size={1.5} />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            nodeColor={(node) =>
              SEVERITY[(node.data as LineageNodeData).severity].hex
            }
            maskColor="transparent"
          />
        </ReactFlow>

        {/* Detail drawer. */}
        <AnimatePresence>
          {selected ? (
            <motion.aside
              key={selected.urn}
              initial={{ x: 380, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 380, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 380, damping: 34 }}
              className="border-line bg-surface/95 absolute inset-y-0 right-0 z-10 w-full max-w-sm overflow-y-auto border-l p-5 backdrop-blur-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-ink text-[15px] font-semibold">{selected.name}</p>
                  <p className="text-faint mt-0.5 text-[11.5px]">{selected.platform}</p>
                </div>
                <button
                  type="button"
                  aria-label="Close details"
                  onClick={() => setSelected(null)}
                  className="text-muted hover:bg-raised hover:text-ink grid size-7 place-items-center rounded-lg transition-colors"
                >
                  <X className="size-4" />
                </button>
              </div>

              <dl className="mt-5 space-y-4">
                <DrawerField label="Risk">
                  <StatusBadge severity={selected.severity} />
                </DrawerField>

                <DrawerField label="Owner">
                  {selected.owner ? (
                    <span className="text-ink-secondary text-[13px]">{selected.owner}</span>
                  ) : (
                    <span className="text-critical flex items-center gap-1.5 text-[13px] font-medium">
                      <UserX className="size-3.5" /> Unassigned
                    </span>
                  )}
                </DrawerField>

                <DrawerField label="Tags">
                  {selected.tags.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {selected.tags.map((tag) => (
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
                </DrawerField>

                <DrawerField label="Description">
                  {selected.description ? (
                    <p className="text-ink-secondary text-[13px] leading-relaxed">
                      {selected.description}
                    </p>
                  ) : (
                    <p className="text-critical text-[12.5px] font-medium">
                      Missing — flagged by the documentation rule.
                    </p>
                  )}
                </DrawerField>

                <DrawerField
                  label={
                    <span className="text-brand-strong flex items-center gap-1">
                      <Sparkles className="size-3" /> AI Summary
                    </span>
                  }
                >
                  <div className="border-brand/25 bg-brand/8 rounded-xl border p-3">
                    <p className="text-ink-secondary text-[12.5px] leading-relaxed">
                      {selected.aiSummary}
                    </p>
                  </div>
                </DrawerField>

                <DrawerField label="URN">
                  <code className="text-faint block text-[10.5px] leading-relaxed break-all">
                    {selected.urn}
                  </code>
                </DrawerField>
              </dl>
            </motion.aside>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}

function DrawerField({
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
