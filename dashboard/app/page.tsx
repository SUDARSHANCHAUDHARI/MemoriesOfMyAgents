import { getStats, getAllMemories, getAllSessions } from "@/lib/moma"
import { Brain, Clock, Globe, AlertTriangle } from "lucide-react"
import MemoryCard from "@/components/MemoryCard"

export const dynamic = "force-dynamic"

export default function HomePage() {
  const stats = getStats()
  const recentMemories = getAllMemories().filter(m => !m.superseded_by).slice(0, 6)
  const recentSessions = getAllSessions().slice(0, 5)

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-bold text-zinc-100">MemoriesOfMyAgents</h1>
        <p className="text-sm text-zinc-500 mt-1">Local-first memory for AI coding agents</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Memories", value: stats.total_memories, icon: Brain },
          { label: "Sessions", value: stats.total_sessions, icon: Clock },
          { label: "Global", value: stats.global_memories, icon: Globe },
          { label: "Conflicts", value: stats.conflicts, icon: AlertTriangle },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-zinc-500">
              <Icon size={14} />
              <span className="text-xs uppercase tracking-wider">{label}</span>
            </div>
            <span className="text-2xl font-bold text-zinc-100">{value}</span>
          </div>
        ))}
      </div>

      {Object.keys(stats.by_type).length > 0 && (
        <div className="border border-zinc-800 rounded-lg p-4">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">By Type</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.by_type).map(([type, count]) => (
              <span key={type} className="text-xs px-2 py-1 bg-zinc-900 text-zinc-300 rounded">
                {type} <span className="text-zinc-500">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {recentSessions.length > 0 && (
        <div>
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Recent Sessions</h2>
          <div className="flex flex-col gap-2">
            {recentSessions.map(s => (
              <div key={s.id} className="border border-zinc-800 rounded-lg p-3 flex items-center justify-between">
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm text-zinc-200">{s.project}</span>
                  <span className="text-xs text-zinc-500">{s.intent?.goal || s.intent?.raw || "—"}</span>
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${s.ended_at ? "text-zinc-500 bg-zinc-900" : "text-green-400 bg-green-950"}`}>
                    {s.ended_at ? "ended" : "active"}
                  </span>
                  <span className="text-[10px] text-zinc-600">{s.git_branch}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {recentMemories.length > 0 && (
        <div>
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Recent Memories</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {recentMemories.map(m => <MemoryCard key={m.id} memory={m} />)}
          </div>
        </div>
      )}

      {recentMemories.length === 0 && (
        <div className="border border-zinc-800 rounded-lg p-8 text-center text-zinc-600 text-sm">
          No memories yet. Start a Claude Code session to begin capturing.
        </div>
      )}
    </div>
  )
}
