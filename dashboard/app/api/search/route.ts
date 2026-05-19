import { NextResponse } from "next/server"
import { searchMemories } from "@/lib/moma"

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const query = searchParams.get("q") || ""
  const project = searchParams.get("project") || undefined
  if (!query.trim()) return NextResponse.json([])
  return NextResponse.json(searchMemories(query, project))
}
