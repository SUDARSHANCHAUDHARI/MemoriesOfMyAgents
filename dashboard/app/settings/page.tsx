import fs from "fs"
import path from "path"
import os from "os"

export const dynamic = "force-dynamic"

const MOMA_ROOT = process.env.MOMA_ROOT || path.join(os.homedir(), ".moma")

function getConfig(): string {
  try {
    return fs.readFileSync(path.join(MOMA_ROOT, "config.json"), "utf-8")
  } catch {
    return "{}"
  }
}

function getDedup(): number {
  try {
    const d = JSON.parse(fs.readFileSync(path.join(MOMA_ROOT, "index", "dedup.json"), "utf-8"))
    return Object.keys(d).length
  } catch { return 0 }
}

export default function SettingsPage() {
  const config = getConfig()
  const dedupCount = getDedup()
  const momaRoot = MOMA_ROOT

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6">
      <h1 className="text-xl font-bold text-zinc-100">Settings</h1>

      <div className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-3">
        <h2 className="text-xs uppercase tracking-wider text-zinc-500">Storage</h2>
        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-sm">
            <span className="text-zinc-400">Root directory</span>
            <span className="text-zinc-300 font-mono text-xs">{momaRoot}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-zinc-400">Dedup entries</span>
            <span className="text-zinc-300">{dedupCount}</span>
          </div>
        </div>
      </div>

      <div className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-3">
        <h2 className="text-xs uppercase tracking-wider text-zinc-500">Config (read-only)</h2>
        <p className="text-xs text-zinc-600">Edit at: <code className="text-zinc-500">{momaRoot}/config.json</code></p>
        <pre className="text-[11px] text-zinc-400 leading-relaxed overflow-x-auto max-h-96 overflow-y-auto bg-zinc-900 p-3 rounded">
          {config}
        </pre>
      </div>

      <div className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-2">
        <h2 className="text-xs uppercase tracking-wider text-zinc-500">Hook Status</h2>
        <p className="text-xs text-zinc-600">Hooks are installed via <code className="text-zinc-500">integrations/claude-code/install.sh</code></p>
        {["session_start", "prompt_submit", "post_tool_use", "pre_tool_use", "stop"].map(h => (
          <div key={h} className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-mono">{h}.py</span>
            <span className="text-[10px] text-green-400 bg-green-950 px-1.5 py-0.5 rounded">active</span>
          </div>
        ))}
      </div>
    </div>
  )
}
