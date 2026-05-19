import { NextResponse } from "next/server"
import { getAllMemories } from "@/lib/moma"

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const project = searchParams.get("project") || undefined
  const type = searchParams.get("type") || undefined
  const scope = searchParams.get("scope") || undefined

  let memories = getAllMemories().filter(m => !m.superseded_by)
  if (project) memories = memories.filter(m => m.project === project || m.scope === "global")
  if (type) memories = memories.filter(m => m.type === type)
  if (scope) memories = memories.filter(m => m.scope === scope)

  return NextResponse.json(memories)
}
