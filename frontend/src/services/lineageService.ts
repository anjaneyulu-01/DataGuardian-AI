/**
 * Lineage graph.
 *
 * Live source: `GET /api/v1/lineage/impact?urn=...`, which returns upstream
 * and downstream in one call.
 *
 * The API returns a node LIST; React Flow needs positioned nodes and edges.
 * Layout happens here, in the service, so the page component stays a renderer
 * and the layout algorithm is testable on its own.
 */

import { apiClient } from './apiClient'
import { withFallback, type Sourced } from './fallback'
import { lineageEdges, lineageNodes } from '@/data/mockData'
import type { ApiImpact, ApiLineageNode } from '@/types/api'
import type {
  LineageGraphEdge,
  LineageGraphNode,
  LineageNodeData,
  Severity,
} from '@/types/domain'

export interface LineageGraph {
  nodes: LineageGraphNode[]
  edges: LineageGraphEdge[]
  rootUrn: string | null
}

// Layout constants. Columns are wide enough that a 224px node card never
// touches its neighbour.
const COLUMN_WIDTH = 300
const ROW_HEIGHT = 130

export async function fetchLineage(urn: string | null): Promise<Sourced<LineageGraph>> {
  if (!urn) {
    return {
      data: { nodes: lineageNodes, edges: lineageEdges, rootUrn: null },
      source: 'demo',
      reason: 'No asset selected — showing an illustrative graph.',
    }
  }

  return withFallback(
    async () => {
      const { data } = await apiClient.get<ApiImpact>('/v1/lineage/impact', {
        params: { urn, count: 20 },
      })
      return buildGraph(urn, data)
    },
    () => ({ nodes: lineageNodes, edges: lineageEdges, rootUrn: null }),
    'lineageService.impact',
  )
}

/**
 * Lay the graph out left-to-right: upstream · root · downstream.
 *
 * A three-column layout rather than a force-directed one because lineage has
 * an inherent direction, and preserving it left-to-right is what makes the
 * graph readable at a glance.
 */
function buildGraph(rootUrn: string, impact: ApiImpact): LineageGraph {
  const nodes: LineageGraphNode[] = []
  const edges: LineageGraphEdge[] = []

  const upstream = impact.upstream?.nodes ?? []
  const downstream = impact.downstream?.nodes ?? []

  const column = (items: ApiLineageNode[], x: number) =>
    items.forEach((item, index) => {
      nodes.push({
        id: item.urn,
        position: {
          x,
          y: index * ROW_HEIGHT - ((items.length - 1) * ROW_HEIGHT) / 2,
        },
        data: toNodeData(item),
      })
    })

  column(upstream, 0)

  // The root sits in the middle column, vertically centred.
  nodes.push({
    id: rootUrn,
    position: { x: COLUMN_WIDTH, y: 0 },
    data: {
      urn: rootUrn,
      name: shortName(rootUrn),
      platform: platformFromUrn(rootUrn),
      kind: 'dataset',
      owner: null,
      severity: 'medium',
      tags: [],
      description: null,
      aiSummary: 'The asset this lineage was traced from.',
      isRoot: true,
    },
  })

  column(downstream, COLUMN_WIDTH * 2)

  for (const node of upstream) {
    edges.push({ id: `${node.urn}->${rootUrn}`, source: node.urn, target: rootUrn })
  }
  for (const node of downstream) {
    edges.push({ id: `${rootUrn}->${node.urn}`, source: rootUrn, target: node.urn })
  }

  return { nodes, edges, rootUrn }
}

function toNodeData(node: ApiLineageNode): LineageNodeData {
  return {
    urn: node.urn,
    name: node.name ?? shortName(node.urn),
    platform: node.platform?.display_name ?? node.platform?.name ?? platformFromUrn(node.urn),
    kind: inferKind(node),
    owner: null,
    severity: node.deprecated ? ('high' as Severity) : ('low' as Severity),
    tags: node.deprecated ? ['deprecated'] : [],
    description: node.description,
    aiSummary: node.deprecated
      ? 'Marked deprecated in DataHub but still present in this lineage path.'
      : `${node.entity_type.toLowerCase()} at hop ${node.degree ?? 1} from the traced asset.`,
  }
}

/**
 * Classify a node for its icon and colour.
 *
 * DataHub's `entity_type` distinguishes dashboards and ML models; datasets are
 * further split into "pipeline" when the platform is a transformation tool,
 * because a dbt model and a Snowflake table read very differently on a graph.
 */
function inferKind(node: ApiLineageNode): LineageNodeData['kind'] {
  const entityType = node.entity_type.toUpperCase()
  if (entityType === 'DASHBOARD' || entityType === 'CHART') return 'dashboard'
  if (entityType === 'MLMODEL' || entityType === 'MLFEATURETABLE') return 'model'
  if (entityType === 'DATAFLOW' || entityType === 'DATAJOB') return 'pipeline'

  const platform = (node.platform?.name ?? platformFromUrn(node.urn)).toLowerCase()
  if (['dbt', 'airflow', 'spark', 'kafka'].includes(platform)) return 'pipeline'
  if (['looker', 'tableau', 'powerbi', 'superset'].includes(platform)) return 'dashboard'
  return 'dataset'
}

/** `urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.fct_x,PROD)` → `fct_x`. */
function shortName(urn: string): string {
  const inner = urn.match(/\(([^)]*)\)/)?.[1]
  const path = inner?.split(',')[1] ?? urn
  return path.split('.').pop() ?? path
}

function platformFromUrn(urn: string): string {
  return urn.match(/dataPlatform:([a-zA-Z0-9_-]+)/)?.[1] ?? 'unknown'
}
