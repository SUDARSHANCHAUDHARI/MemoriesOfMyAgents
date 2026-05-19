"use client"
import { useState } from "react"
import MemoryCard from "@/components/MemoryCard"
import type { Memory } from "@/lib/moma"
import { Search } from "lucide-react"

export default function SearchPage() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<Memory[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
    const data = await res.json()
    setResults(data)
    setSearched(true)
    setLoading(false)
  }

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      <h1 className="text-xl font-bold text-zinc-100">Search</h1>

      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search memories..."
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg pl-9 pr-4 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-zinc-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-sm rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? "..." : "Search"}
        </button>
      </form>

      {searched && (
        <div className="flex flex-col gap-3">
          <span className="text-xs text-zinc-500">{results.length} results for "{query}"</span>
          {results.length === 0 ? (
            <div className="border border-zinc-800 rounded-lg p-8 text-center text-zinc-600 text-sm">
              No memories found.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {results.map(m => <MemoryCard key={m.id} memory={m} />)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
