import { getGuardLocks, getConflicts } from "@/lib/moma"
import { Shield, AlertTriangle } from "lucide-react"

export const dynamic = "force-dynamic"

const ACTION_STYLES: Record<string, string> = {
  block: "text-red-400 bg-red-950",
  warn: "text-yellow-400 bg-yellow-950",
  confirm: "text-blue-400 bg-blue-950",
  allow: "text-green-400 bg-green-950",
}

export default function GuardLocksPage() {
  const guardlocks = getGuardLocks()
  const conflicts = getConflicts()

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-8">
      <h1 className="text-xl font-bold text-zinc-100">GuardLocks</h1>

      {/* Active rules */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Shield size={14} className="text-zinc-500" />
          <h2 className="text-xs uppercase tracking-wider text-zinc-500">Active Rules ({guardlocks.length})</h2>
        </div>
        {guardlocks.length === 0 ? (
          <div className="border border-zinc-800 rounded-lg p-6 text-center text-zinc-600 text-sm">
            No GuardLocks configured. Add rules to <code className="text-zinc-500">~/.moma/config.json</code>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {guardlocks.map(gl => (
              <div key={gl.id} className="border border-zinc-800 rounded-lg p-4 flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <span className="text-sm font-semibold text-zinc-100">{gl.name}</span>
                  <span className="text-xs text-zinc-400">{gl.message}</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(gl.pattern || {}).map(([k, v]) => (
                      <span key={k} className="text-[10px] px-1.5 py-0.5 bg-zinc-900 text-zinc-500 rounded font-mono">
                        {k}: {v}
                      </span>
                    ))}
                  </div>
                </div>
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded shrink-0 ${ACTION_STYLES[gl.action] || ACTION_STYLES.warn}`}>
                  {gl.action}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Conflicts */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle size={14} className="text-zinc-500" />
          <h2 className="text-xs uppercase tracking-wider text-zinc-500">Memory Conflicts ({conflicts.length})</h2>
        </div>
        {conflicts.length === 0 ? (
          <div className="border border-zinc-800 rounded-lg p-6 text-center text-zinc-600 text-sm">
            No conflicts detected.
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {conflicts.slice().reverse().map((c, i) => (
              <div key={i} className="border border-orange-900 rounded-lg p-4 flex flex-col gap-1">
                <span className="text-xs text-orange-400">{c.reason}</span>
                <div className="flex gap-2 text-[10px] text-zinc-600 font-mono">
                  <span>old: {c.old_memory_id}</span>
                  <span>→</span>
                  <span>new: {c.new_memory_id}</span>
                </div>
                <span className="text-[10px] text-zinc-700">{new Date(c.detected_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* How to add GuardLocks */}
      <div className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-2">
        <h3 className="text-xs uppercase tracking-wider text-zinc-500 mb-1">Add a GuardLock</h3>
        <pre className="text-[11px] text-zinc-400 leading-relaxed overflow-x-auto">{`// ~/.moma/config.json → guardlocks array
{
  "id": "gl_001",
  "name": "No direct main commits",
  "pattern": { "branch": "main|master" },
  "action": "block",
  "message": "Create a feature branch first."
}`}</pre>
      </div>
    </div>
  )
}
