"use client"
import { useEffect, useRef, useState } from "react"

interface Observation {
  id: string
  session_id: string
  timestamp: string
  tool: string
  importance_hint: number
  output_tail: string
}

const WS_URL = "ws://localhost:7842"
const SSE_URL = "/api/stream"

const IMPORTANCE_COLOR: Record<number, string> = {
  9: "text-red-400",
  8: "text-orange-400",
  7: "text-yellow-400",
  6: "text-blue-400",
  5: "text-zinc-300",
}

function importanceColor(n: number): string {
  return IMPORTANCE_COLOR[n] || "text-zinc-500"
}

export default function LivePage() {
  const [observations, setObservations] = useState<Observation[]>([])
  const [connected, setConnected] = useState(false)
  const [transport, setTransport] = useState<"ws" | "sse" | "none">("none")
  const [paused, setPaused] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const pausedRef = useRef(false)
  const wsRef = useRef<WebSocket | null>(null)
  const esRef = useRef<EventSource | null>(null)
  pausedRef.current = paused

  function handleMessage(data: string) {
    if (pausedRef.current) return
    try {
      const obs = JSON.parse(data) as Observation
      setObservations(prev => [obs, ...prev].slice(0, 500))
    } catch {}
  }

  useEffect(() => {
    let sseTimeout: ReturnType<typeof setTimeout>

    function connectSSE() {
      const es = new EventSource(SSE_URL)
      esRef.current = es
      es.onopen = () => { setConnected(true); setTransport("sse") }
      es.onerror = () => { setConnected(false); setTransport("none") }
      es.onmessage = (e) => handleMessage(e.data)
    }

    function connectWS() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        clearTimeout(sseTimeout)
        esRef.current?.close()
        setConnected(true)
        setTransport("ws")
      }

      ws.onmessage = (e) => handleMessage(e.data)

      ws.onerror = () => {
        // WS failed — fall back to SSE
        ws.close()
      }

      ws.onclose = () => {
        if (wsRef.current === ws) {
          setConnected(false)
          setTransport("none")
          // SSE fallback after WS closes
          sseTimeout = setTimeout(connectSSE, 500)
        }
      }
    }

    // Try WS first; give it 2s to connect before also starting SSE
    connectWS()
    sseTimeout = setTimeout(() => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        connectSSE()
      }
    }, 2000)

    return () => {
      clearTimeout(sseTimeout)
      wsRef.current?.close()
      wsRef.current = null
      esRef.current?.close()
      esRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [observations, paused])

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-4 h-[calc(100vh-6rem)]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Live Stream</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Real-time observation feed from all active sessions</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`flex items-center gap-1.5 text-xs ${connected ? "text-green-400" : "text-red-400"}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
            {connected ? (
              <>{transport === "ws" ? "WebSocket" : "SSE"} connected</>
            ) : "disconnected"}
          </span>
          <button
            onClick={() => setPaused(p => !p)}
            className="text-xs px-3 py-1 border border-zinc-700 rounded hover:border-zinc-500 text-zinc-400 hover:text-zinc-200"
          >
            {paused ? "▶ Resume" : "⏸ Pause"}
          </button>
          <button
            onClick={() => setObservations([])}
            className="text-xs px-3 py-1 border border-zinc-700 rounded hover:border-zinc-500 text-zinc-400 hover:text-zinc-200"
          >
            Clear
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto border border-zinc-800 rounded-lg font-mono text-xs">
        {observations.length === 0 ? (
          <div className="flex items-center justify-center h-full text-zinc-600">
            Waiting for observations... Start a session or run the filesystem watcher.
          </div>
        ) : (
          <div className="flex flex-col-reverse">
            {observations.map(obs => (
              <div key={obs.id} className="flex gap-3 px-4 py-2 border-b border-zinc-900 hover:bg-zinc-900/50">
                <span className="text-zinc-700 shrink-0 w-20">
                  {new Date(obs.timestamp).toLocaleTimeString()}
                </span>
                <span className={`shrink-0 w-6 text-center font-bold ${importanceColor(obs.importance_hint)}`}>
                  {obs.importance_hint}
                </span>
                <span className="text-purple-400 shrink-0 w-28 truncate">{obs.tool}</span>
                <span className="text-zinc-400 shrink-0 w-24 truncate">{obs.session_id.slice(-8)}</span>
                <span className="text-zinc-300 truncate">{obs.output_tail.slice(0, 120)}</span>
              </div>
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="text-xs text-zinc-600 flex gap-4">
        <span>{observations.length} events</span>
        <span className="text-red-400">■ 9=failure</span>
        <span className="text-orange-400">■ 8=subagent</span>
        <span className="text-yellow-400">■ 7=write/edit</span>
        <span className="text-blue-400">■ 6=compact</span>
        <span className="text-zinc-400">■ 5=bash</span>
      </div>
    </div>
  )
}
