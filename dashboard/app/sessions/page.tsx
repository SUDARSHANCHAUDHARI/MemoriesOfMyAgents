import Link from "next/link"
import { getAllSessions } from "@/lib/moma"

export const dynamic = "force-dynamic"

function duration(start: string, end: string | null): string {
  if (!end) return "active"
  const ms = new Date(end).getTime() - new Date(start).getTime()
  const mins = Math.floor(ms / 60000)
  return mins < 60 ? `${mins}m` : `${Math.floor(mins / 60)}h ${mins % 60}m`
}

export default function SessionsPage() {
  const sessions = getAllSessions()

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-zinc-100">Sessions</h1>
        <span className="text-sm text-zinc-500">{sessions.length} total</span>
      </div>

      {sessions.length === 0 ? (
        <div className="border border-zinc-800 rounded-lg p-8 text-center text-zinc-600 text-sm">
          No sessions recorded yet.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {sessions.map(s => (
            <div key={s.id} className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-2">
              <div className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-100">{s.project}</span>
                    {s.git_branch && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-zinc-900 text-zinc-500 rounded">{s.git_branch}</span>
                    )}
                  </div>
                  {s.intent?.goal && (
                    <p className="text-xs text-zinc-400">{s.intent.goal}</p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${s.ended_at ? "text-zinc-500 bg-zinc-900" : "text-green-400 bg-green-950"}`}>
                    {s.ended_at ? duration(s.started_at, s.ended_at) : "active"}
                  </span>
                  <span className="text-[10px] text-zinc-600">
                    {new Date(s.started_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {s.intent && (
                <div className="flex flex-wrap gap-2 mt-1">
                  {s.intent.task_type !== "unknown" && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-zinc-900 text-zinc-400 rounded">{s.intent.task_type}</span>
                  )}
                  {s.intent.domain && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-zinc-900 text-zinc-400 rounded">{s.intent.domain}</span>
                  )}
                  {s.agent && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-zinc-900 text-zinc-400 rounded">{s.agent}</span>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between">
                <span className="text-[10px] text-zinc-700 font-mono">{s.id}</span>
                {s.ended_at && (
                  <Link href={`/replay/${s.id}`} className="text-[10px] px-2 py-0.5 border border-zinc-700 rounded text-zinc-500 hover:text-zinc-300 hover:border-zinc-500">
                    ▶ Replay
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
