"use client"
import { useEffect, useRef, useState } from "react"

interface Node {
  id: string
  label: string
  type: string
  project: string
  importance: number
  node_kind: "memory" | "concept"
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface Edge {
  from: string
  to: string
  relation: string
  weight: number
}

interface GraphData {
  nodes: Node[]
  edges: Edge[]
}

const NODE_COLORS: Record<string, string> = {
  memory: "#a855f7",
  concept: "#3b82f6",
}

const TYPE_COLORS: Record<string, string> = {
  bug: "#ef4444",
  architecture: "#f59e0b",
  preference: "#10b981",
  workflow: "#06b6d4",
  fact: "#6366f1",
  pattern: "#ec4899",
}

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] })
  const [selected, setSelected] = useState<Node | null>(null)
  const [filter, setFilter] = useState<"all" | "memory" | "concept">("all")
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const nodesRef = useRef<Node[]>([])
  const animRef = useRef<number>(0)

  useEffect(() => {
    fetch("/api/graph")
      .then(r => r.json())
      .then((data: GraphData) => {
        // Initialize positions with force-directed layout seed
        const w = 800, h = 600
        const nodes = data.nodes.map((n, i) => ({
          ...n,
          x: w / 2 + Math.cos((i / data.nodes.length) * Math.PI * 2) * 200 + (Math.random() - 0.5) * 100,
          y: h / 2 + Math.sin((i / data.nodes.length) * Math.PI * 2) * 200 + (Math.random() - 0.5) * 100,
          vx: 0,
          vy: 0,
        }))
        nodesRef.current = nodes
        setGraph({ ...data, nodes })
      })
  }, [])

  useEffect(() => {
    if (graph.nodes.length === 0) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")!
    const nodeMap = new Map(nodesRef.current.map(n => [n.id, n]))

    const simulate = () => {
      const nodes = nodesRef.current
      if (nodes.length === 0) return

      // Repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j]
          const dx = (b.x || 0) - (a.x || 0)
          const dy = (b.y || 0) - (a.y || 0)
          const dist = Math.sqrt(dx * dx + dy * dy) + 0.1
          const force = 3000 / (dist * dist)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          a.vx = (a.vx || 0) - fx * 0.01
          a.vy = (a.vy || 0) - fy * 0.01
          b.vx = (b.vx || 0) + fx * 0.01
          b.vy = (b.vy || 0) + fy * 0.01
        }
      }

      // Attraction along edges
      for (const edge of graph.edges) {
        const a = nodeMap.get(edge.from)
        const b = nodeMap.get(edge.to)
        if (!a || !b) continue
        const dx = (b.x || 0) - (a.x || 0)
        const dy = (b.y || 0) - (a.y || 0)
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1
        const force = (dist - 80) * 0.003 * (edge.weight || 1)
        a.vx = (a.vx || 0) + (dx / dist) * force
        a.vy = (a.vy || 0) + (dy / dist) * force
        b.vx = (b.vx || 0) - (dx / dist) * force
        b.vy = (b.vy || 0) - (dy / dist) * force
      }

      // Center gravity + damping + boundary
      const cx = canvas.width / 2, cy = canvas.height / 2
      for (const n of nodes) {
        n.vx = ((n.vx || 0) + (cx - (n.x || 0)) * 0.0002) * 0.85
        n.vy = ((n.vy || 0) + (cy - (n.y || 0)) * 0.0002) * 0.85
        n.x = Math.max(20, Math.min(canvas.width - 20, (n.x || 0) + n.vx))
        n.y = Math.max(20, Math.min(canvas.height - 20, (n.y || 0) + n.vy))
      }

      // Draw
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = "#09090b"
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // Edges
      for (const edge of graph.edges) {
        const a = nodeMap.get(edge.from)
        const b = nodeMap.get(edge.to)
        if (!a || !b) continue
        const visible = filter === "all" || (filter === "memory" && (a.node_kind === "memory" || b.node_kind === "memory"))
        if (!visible) continue
        ctx.beginPath()
        ctx.moveTo(a.x || 0, a.y || 0)
        ctx.lineTo(b.x || 0, b.y || 0)
        ctx.strokeStyle = `rgba(63,63,70,${Math.min(1, (edge.weight || 1) * 0.3)})`
        ctx.lineWidth = Math.min(3, edge.weight || 1)
        ctx.stroke()
      }

      // Nodes
      for (const n of nodes) {
        if (filter !== "all" && n.node_kind !== filter) continue
        const r = n.node_kind === "memory" ? 8 + n.importance : 5
        ctx.beginPath()
        ctx.arc(n.x || 0, n.y || 0, r, 0, Math.PI * 2)
        ctx.fillStyle = n.node_kind === "memory"
          ? (TYPE_COLORS[n.type] || NODE_COLORS.memory)
          : NODE_COLORS.concept
        ctx.fill()
        if (selected?.id === n.id) {
          ctx.strokeStyle = "#fff"
          ctx.lineWidth = 2
          ctx.stroke()
        }
        ctx.fillStyle = "rgba(228,228,231,0.8)"
        ctx.font = "9px monospace"
        ctx.fillText(n.label.slice(0, 20), (n.x || 0) + r + 2, (n.y || 0) + 3)
      }

      animRef.current = requestAnimationFrame(simulate)
    }

    simulate()
    return () => cancelAnimationFrame(animRef.current)
  }, [graph, filter, selected])

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    for (const n of nodesRef.current) {
      const dx = (n.x || 0) - mx
      const dy = (n.y || 0) - my
      if (Math.sqrt(dx * dx + dy * dy) < 14) {
        setSelected(n)
        return
      }
    }
    setSelected(null)
  }

  const stats = {
    nodes: graph.nodes.length,
    edges: graph.edges.length,
    memories: graph.nodes.filter(n => n.node_kind === "memory").length,
    concepts: graph.nodes.filter(n => n.node_kind === "concept").length,
  }

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Knowledge Graph</h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            {stats.nodes} nodes · {stats.edges} edges · {stats.memories} memories · {stats.concepts} concepts
          </p>
        </div>
        <div className="flex gap-2">
          {(["all", "memory", "concept"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1 rounded border ${filter === f ? "border-purple-500 text-purple-300" : "border-zinc-700 text-zinc-500 hover:text-zinc-300"}`}
            >{f}</button>
          ))}
        </div>
      </div>

      <div className="flex gap-4">
        <canvas
          ref={canvasRef}
          width={800}
          height={550}
          onClick={handleCanvasClick}
          className="border border-zinc-800 rounded-lg cursor-pointer flex-1"
          style={{ background: "#09090b" }}
        />

        {selected && (
          <div className="w-56 border border-zinc-800 rounded-lg p-4 flex flex-col gap-2 text-xs shrink-0">
            <div className="text-zinc-100 font-semibold break-words">{selected.label}</div>
            <div className="flex flex-col gap-1 text-zinc-500">
              <span>kind: <span className="text-zinc-300">{selected.node_kind}</span></span>
              <span>type: <span className="text-zinc-300">{selected.type}</span></span>
              <span>project: <span className="text-zinc-300">{selected.project}</span></span>
              {selected.node_kind === "memory" && (
                <span>importance: <span className="text-zinc-300">{selected.importance}</span></span>
              )}
              <span className="text-zinc-700 break-all mt-1">{selected.id}</span>
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-4 text-xs text-zinc-600 flex-wrap">
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: color }} />
            {type}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full inline-block bg-blue-500" />concept
        </span>
      </div>

      {graph.nodes.length === 0 && (
        <div className="text-center text-zinc-600 py-12 text-sm">
          No graph data yet. Memories are added to the graph automatically during compression.
        </div>
      )}
    </div>
  )
}
