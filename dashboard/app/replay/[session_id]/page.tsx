"use client"
import { useEffect, useRef, useState } from "react"
import { useParams } from "next/navigation"

interface Observation {
  id: string
  timestamp: string
  tool: string
  importance_hint: number
  output_tail: string
}

interface ReplayData {
  session: {
    project: string
    agent: string
    started_at: string
    ended_at: string | null
    intent?: { goal?: string; raw?: string }
  } | null
  observations: Observation[]
}

export default function ReplayPage() {
  const params = useParams<{ session_id: string }>()
  const sessionId = params.session_id
  const [data, setData] = useState<ReplayData | null>(null)
  const [cursor, setCursor] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetch(`/api/replay/${sessionId}`)
      .then(r => r.json())
      .then(setData)
  }, [sessionId])

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (!playing || !data) return
    const delay = Math.max(100, 500 / speed)
    intervalRef.current = setInterval(() => {
      setCursor(c => {
        if (c >= data.observations.length - 1) {
          setPlaying(false)
          return c
        }
        return c + 1
      })
    }, delay)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [playing, speed, data])

  if (!data) {
    return <div className="text-zinc-500 text-sm p-8">Loading replay...</div>
  }

  const obs = data.observations
  const visible = obs.slice(0, cursor + 1)
  const current = obs[cursor]
  const progress = obs.length > 0 ? ((cursor + 1) / obs.length) * 100 : 0

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-bold text-zinc-100">Session Replay</h1>
        <p className="text-xs text-zinc-500 mt-0.5 font-mono">{sessionId}</p>
      </div>

      {data.session && (
        <div className="border border-zinc-800 rounded-lg p-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div><span className="text-zinc-600">Project </span><span className="text-zinc-200">{data.session.project}</span></div>
          <div><span className="text-zinc-600">Agent </span><span className="text-zinc-200">{data.session.agent}</span></div>
          <div><span className="text-zinc-600">Events </span><span className="text-zinc-200">{obs.length}</span></div>
          <div><span className="text-zinc-600">Goal </span><span className="text-zinc-200 truncate">{data.session.intent?.goal || data.session.intent?.raw || "—"}</span></div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => { setCursor(0); setPlaying(false) }}
          className="text-xs px-3 py-1 border border-zinc-700 rounded text-zinc-400 hover:text-zinc-200"
        >⏮</button>
        <button
          onClick={() => setPlaying(p => !p)}
          className="text-sm px-4 py-1.5 border border-zinc-700 rounded text-zinc-200 hover:border-zinc-500"
        >
          {playing ? "⏸ Pause" : "▶ Play"}
        </button>
        <button
          onClick={() => { setCursor(obs.length - 1); setPlaying(false) }}
          className="text-xs px-3 py-1 border border-zinc-700 rounded text-zinc-400 hover:text-zinc-200"
        >⏭</button>
        <div className="flex items-center gap-1 text-xs text-zinc-500">
          Speed:
          {[0.5, 1, 2, 4].map(s => (
            <button key={s} onClick={() => setSpeed(s)}
              className={`px-2 py-0.5 rounded ${speed === s ? "bg-zinc-700 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}
            >{s}×</button>
          ))}
        </div>
        <span className="text-xs text-zinc-600 ml-auto">{cursor + 1} / {obs.length}</span>
      </div>

      {/* Scrubber */}
      <input
        type="range" min={0} max={Math.max(0, obs.length - 1)} value={cursor}
        onChange={e => { setPlaying(false); setCursor(parseInt(e.target.value)) }}
        className="w-full accent-purple-500"
      />
      <div className="h-1 bg-zinc-800 rounded">
        <div className="h-1 bg-purple-500 rounded transition-all" style={{ width: `${progress}%` }} />
      </div>

      {/* Current event detail */}
      {current && (
        <div className="border border-zinc-800 rounded-lg p-4 font-mono text-xs">
          <div className="flex gap-4 mb-2">
            <span className="text-zinc-500">{new Date(current.timestamp).toLocaleTimeString()}</span>
            <span className="text-purple-400">{current.tool}</span>
            <span className={`font-bold ${current.importance_hint >= 8 ? "text-red-400" : current.importance_hint >= 6 ? "text-yellow-400" : "text-zinc-400"}`}>
              importance: {current.importance_hint}
            </span>
          </div>
          <pre className="text-zinc-300 whitespace-pre-wrap break-all max-h-40 overflow-y-auto">{current.output_tail.slice(0, 800)}</pre>
        </div>
      )}

      {/* Timeline */}
      <div className="border border-zinc-800 rounded-lg overflow-hidden max-h-80 overflow-y-auto">
        <div className="font-mono text-xs">
          {visible.map((o, i) => (
            <div
              key={o.id}
              onClick={() => setCursor(i)}
              className={`flex gap-3 px-4 py-1.5 border-b border-zinc-900 cursor-pointer ${i === cursor ? "bg-zinc-800" : "hover:bg-zinc-900/50"}`}
            >
              <span className="text-zinc-700 w-20 shrink-0">{new Date(o.timestamp).toLocaleTimeString()}</span>
              <span className={`w-4 shrink-0 font-bold ${o.importance_hint >= 8 ? "text-red-400" : o.importance_hint >= 6 ? "text-yellow-400" : "text-zinc-500"}`}>
                {o.importance_hint}
              </span>
              <span className="text-purple-400 w-28 shrink-0 truncate">{o.tool}</span>
              <span className="text-zinc-400 truncate">{o.output_tail.slice(0, 80)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
