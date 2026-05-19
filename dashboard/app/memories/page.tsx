import { getAllMemories, getStats } from "@/lib/moma"
import MemoryCard from "@/components/MemoryCard"

export const dynamic = "force-dynamic"

const TYPES = ["architecture","pattern","preference","bug","workflow","fact","conflict"]

export default async function MemoriesPage({ searchParams }: { searchParams: Promise<Record<string, string>> }) {
  const params = await searchParams
  const type = params?.type
  const scope = params?.scope
  const project = params?.project

  let memories = getAllMemories().filter(m => !m.superseded_by)
  if (type) memories = memories.filter(m => m.type === type)
  if (scope) memories = memories.filter(m => m.scope === scope)
  if (project) memories = memories.filter(m => m.project === project || m.scope === "global")

  const stats = getStats()
  const projects = stats.projects

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-zinc-100">Memories</h1>
        <span className="text-sm text-zinc-500">{memories.length} total</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <a href="/memories" className={`text-xs px-2 py-1 rounded border transition-colors ${!type && !scope ? "border-zinc-400 text-zinc-100" : "border-zinc-700 text-zinc-500 hover:text-zinc-300"}`}>
          All
        </a>
        {TYPES.map(t => (
          <a key={t} href={`/memories?type=${t}`} className={`text-xs px-2 py-1 rounded border transition-colors ${type === t ? "border-zinc-400 text-zinc-100" : "border-zinc-700 text-zinc-500 hover:text-zinc-300"}`}>
            {t}
          </a>
        ))}
        <a href="/memories?scope=global" className={`text-xs px-2 py-1 rounded border transition-colors ${scope === "global" ? "border-zinc-400 text-zinc-100" : "border-zinc-700 text-zinc-500 hover:text-zinc-300"}`}>
          global
        </a>
      </div>

      {/* Project filter */}
      {projects.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {projects.map(p => (
            <a key={p} href={`/memories?project=${p}`} className={`text-xs px-2 py-1 rounded bg-zinc-900 transition-colors ${project === p ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}>
              {p}
            </a>
          ))}
        </div>
      )}

      {memories.length === 0 ? (
        <div className="border border-zinc-800 rounded-lg p-8 text-center text-zinc-600 text-sm">
          No memories match the current filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {memories.map(m => <MemoryCard key={m.id} memory={m} />)}
        </div>
      )}
    </div>
  )
}
