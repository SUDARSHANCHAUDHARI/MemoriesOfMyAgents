import fs from "fs"
import path from "path"
import os from "os"

const MOMA_ROOT = process.env.MOMA_ROOT || path.join(os.homedir(), ".moma")

export interface Memory {
  id: string
  type: string
  scope: "project" | "global"
  project: string
  title: string
  content: string
  concepts: string[]
  files: string[]
  importance: number
  confidence: number
  created_at: string
  updated_at: string
  session_ids: string[]
  supersedes: string[]
  superseded_by: string | null
}

export interface Session {
  id: string
  project: string
  project_slug: string
  cwd: string
  agent: string
  git_branch: string
  model: string
  started_at: string
  ended_at: string | null
  intent: {
    raw: string
    task_type: string
    domain: string
    files_mentioned: string[]
    goal: string
  } | null
}

export interface Conflict {
  old_memory_id: string
  new_memory_id: string
  reason: string
  detected_at: string
}

export interface GuardLock {
  id: string
  name: string
  pattern: Record<string, string>
  action: "allow" | "warn" | "block" | "confirm"
  message: string
  enabled?: boolean
}

// ── readers ──────────────────────────────────────────────────────────────

function parseFrontmatter(text: string): Record<string, string> {
  const parts = text.split("---")
  if (parts.length < 3) return {}
  const fm: Record<string, string> = {}
  for (const line of parts[1].trim().split("\n")) {
    const idx = line.indexOf(":")
    if (idx === -1) continue
    fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
  }
  return fm
}

function parseJsonField(val: string | undefined): unknown {
  if (!val) return []
  try { return JSON.parse(val) } catch { return val }
}

function parseMemoryFile(filePath: string): Memory | null {
  try {
    const text = fs.readFileSync(filePath, "utf-8")
    if (!text.startsWith("---")) return null
    const parts = text.split("---")
    if (parts.length < 3) return null
    const fm = parseFrontmatter(text)
    const body = parts.slice(2).join("---").trim()
    const lines = body.split("\n")
    const title = lines[0]?.trim() || ""
    const content = lines.slice(2).join("\n").trim()
    return {
      id: fm.id || "",
      type: fm.type || "fact",
      scope: (fm.scope as "project" | "global") || "project",
      project: fm.project || "",
      title,
      content,
      concepts: parseJsonField(fm.concepts) as string[],
      files: parseJsonField(fm.files) as string[],
      importance: parseInt(fm.importance || "5"),
      confidence: parseFloat(fm.confidence || "0.8"),
      created_at: fm.created_at || "",
      updated_at: fm.updated_at || "",
      session_ids: parseJsonField(fm.session_ids) as string[],
      supersedes: parseJsonField(fm.supersedes) as string[],
      superseded_by: parseJsonField(fm.superseded_by) as string | null,
    }
  } catch {
    return null
  }
}

function walkDir(dir: string): string[] {
  if (!fs.existsSync(dir)) return []
  const results: string[] = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) results.push(...walkDir(full))
    else if (entry.name.endsWith(".md")) results.push(full)
  }
  return results
}

export function getAllMemories(): Memory[] {
  const memoriesDir = path.join(MOMA_ROOT, "memories")
  const files = walkDir(memoriesDir)
  return files.flatMap(f => {
    const m = parseMemoryFile(f)
    return m ? [m] : []
  }).sort((a, b) => b.updated_at.localeCompare(a.updated_at))
}

export function getAllSessions(): Session[] {
  const sessionsDir = path.join(MOMA_ROOT, "sessions")
  if (!fs.existsSync(sessionsDir)) return []
  return fs.readdirSync(sessionsDir)
    .filter(f => f.endsWith(".json"))
    .flatMap(f => {
      try {
        return [JSON.parse(fs.readFileSync(path.join(sessionsDir, f), "utf-8")) as Session]
      } catch { return [] }
    })
    .sort((a, b) => b.started_at.localeCompare(a.started_at))
}

export function getConflicts(): Conflict[] {
  const p = path.join(MOMA_ROOT, "index", "conflicts.json")
  if (!fs.existsSync(p)) return []
  try { return JSON.parse(fs.readFileSync(p, "utf-8")) } catch { return [] }
}

export function getGuardLocks(): GuardLock[] {
  const p = path.join(MOMA_ROOT, "config.json")
  if (!fs.existsSync(p)) return []
  try {
    const config = JSON.parse(fs.readFileSync(p, "utf-8"))
    return config.guardlocks || []
  } catch { return [] }
}

export function getStats() {
  const memories = getAllMemories()
  const sessions = getAllSessions()
  const active = memories.filter(m => !m.superseded_by)
  const byType = active.reduce((acc, m) => {
    acc[m.type] = (acc[m.type] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  const projects = [...new Set(memories.map(m => m.project).filter(Boolean))]
  return {
    total_memories: active.length,
    total_sessions: sessions.length,
    by_type: byType,
    projects,
    conflicts: getConflicts().length,
    global_memories: active.filter(m => m.scope === "global").length,
  }
}

export function searchMemories(query: string, project?: string): Memory[] {
  const keywords = query.toLowerCase().split(/\s+/).filter(Boolean)
  return getAllMemories().filter(m => {
    if (m.superseded_by) return false
    if (project && m.project !== project && m.scope !== "global") return false
    const text = `${m.title} ${m.content} ${m.concepts.join(" ")}`.toLowerCase()
    return keywords.some(kw => text.includes(kw))
  })
}
