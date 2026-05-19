import type { Memory } from "@/lib/moma"

const TYPE_COLORS: Record<string, string> = {
  architecture: "text-blue-400 bg-blue-950",
  pattern: "text-purple-400 bg-purple-950",
  preference: "text-yellow-400 bg-yellow-950",
  bug: "text-red-400 bg-red-950",
  workflow: "text-green-400 bg-green-950",
  fact: "text-zinc-400 bg-zinc-800",
  conflict: "text-orange-400 bg-orange-950",
}

function ImportanceDots({ value }: { value: number }) {
  return (
    <span className="flex gap-0.5">
      {Array.from({ length: 10 }).map((_, i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < value ? "bg-zinc-300" : "bg-zinc-700"}`}
        />
      ))}
    </span>
  )
}

export default function MemoryCard({ memory }: { memory: Memory }) {
  const typeStyle = TYPE_COLORS[memory.type] || TYPE_COLORS.fact
  const date = memory.updated_at ? new Date(memory.updated_at).toLocaleDateString() : ""

  return (
    <div className="border border-zinc-800 rounded-lg p-4 flex flex-col gap-2 hover:border-zinc-600 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${typeStyle}`}>
          {memory.type}
        </span>
        <div className="flex items-center gap-2">
          {memory.scope === "global" && (
            <span className="text-[10px] text-zinc-500 uppercase tracking-wider">global</span>
          )}
          <ImportanceDots value={memory.importance} />
        </div>
      </div>
      <p className="text-sm font-semibold text-zinc-100 leading-snug">{memory.title}</p>
      <p className="text-xs text-zinc-400 leading-relaxed">{memory.content}</p>
      {memory.concepts.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {memory.concepts.slice(0, 5).map(c => (
            <span key={c} className="text-[10px] px-1.5 py-0.5 bg-zinc-900 text-zinc-500 rounded">
              {c}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between mt-1">
        <span className="text-[10px] text-zinc-600">{memory.project}</span>
        <span className="text-[10px] text-zinc-600">{date}</span>
      </div>
    </div>
  )
}
