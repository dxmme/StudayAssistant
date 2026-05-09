'use client'

import { memo, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import '@xyflow/react/dist/style.css'

interface GraphNode {
  id: string
  name: string | null
  summary: string | null
  type: string | null
}

interface GraphEdge {
  src: string
  dst: string
  relation: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

type ConceptNodeData = Record<string, unknown> & {
  label: string
  summary: string | null
  conceptType: string | null
  reviewHref: string
}

type ConceptFlowNode = Node<ConceptNodeData>

const NODE_W = 160
const NODE_H = 40

function buildFlowGraph(
  rawNodes: GraphNode[],
  rawEdges: GraphEdge[],
  reviewHref: string,
): { nodes: ConceptFlowNode[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80 })
  g.setDefaultEdgeLabel(() => ({}))

  rawNodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  rawEdges.forEach((e) => g.setEdge(e.src, e.dst))
  dagre.layout(g)

  const nodes: ConceptFlowNode[] = rawNodes.map((n) => {
    const pos = g.node(n.id)
    return {
      id: n.id,
      type: 'conceptNode',
      position: { x: (pos?.x ?? 0) - NODE_W / 2, y: (pos?.y ?? 0) - NODE_H / 2 },
      data: {
        label: n.name ?? n.id,
        summary: n.summary,
        conceptType: n.type,
        reviewHref,
      },
    }
  })

  const edges: Edge[] = rawEdges.map((e, i) => ({
    id: `e-${i}`,
    source: e.src,
    target: e.dst,
    label: e.relation,
  }))

  return { nodes, edges }
}

const ConceptNode = memo(function ConceptNode({ data }: NodeProps<ConceptFlowNode>) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className="px-3 py-2 bg-white border border-gray-300 rounded-lg shadow-sm cursor-pointer hover:border-blue-400 transition-colors relative"
      style={{ width: NODE_W }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <Handle type="target" position={Position.Top} />
      <span className="text-sm font-medium truncate block">{data.label}</span>
      {hovered && (data.summary !== null || data.conceptType !== null) && (
        <div className="absolute bottom-full left-0 mb-2 w-56 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 z-10 shadow-lg">
          {data.conceptType !== null && (
            <p className="text-gray-400 mb-1">{data.conceptType}</p>
          )}
          {data.summary !== null && <p>{data.summary}</p>}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
})

interface Props {
  courseId: string
}

export function ConceptGraph({ courseId }: Props) {
  const [flowNodes, setFlowNodes] = useState<ConceptFlowNode[]>([])
  const [flowEdges, setFlowEdges] = useState<Edge[]>([])
  const [phase, setPhase] = useState<'loading' | 'ready' | 'empty' | 'error'>('loading')
  const nodeTypes = useMemo(() => ({ conceptNode: ConceptNode }), [])
  const router = useRouter()

  useEffect(() => {
    fetch(`/api/courses/${courseId}/graph`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<GraphData>
      })
      .then((data) => {
        if (data.nodes.length === 0) {
          setPhase('empty')
          return
        }
        const reviewHref = `/courses/${courseId}/review`
        const { nodes, edges } = buildFlowGraph(data.nodes, data.edges, reviewHref)
        setFlowNodes(nodes)
        setFlowEdges(edges)
        setPhase('ready')
      })
      .catch(() => setPhase('error'))
  }, [courseId])

  if (phase === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-screen text-gray-400">
        Lade Graph…
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="flex items-center justify-center min-h-screen text-red-500">
        Graph konnte nicht geladen werden.
      </div>
    )
  }

  if (phase === 'empty') {
    return (
      <div className="flex items-center justify-center min-h-screen text-gray-400">
        Keine Concepts gefunden.
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen">
      <header className="flex items-center gap-4 px-6 py-4 border-b border-gray-200">
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          ← Zurück
        </button>
        <h1 className="text-lg font-semibold">Concept Graph</h1>
      </header>
      <div className="flex-1" style={{ minHeight: 'calc(100vh - 65px)' }}>
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          fitView
          onNodeClick={(_e, node) => router.push((node.data as ConceptNodeData).reviewHref)}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}
