import fs from "fs"
import path from "path"
import os from "os"
import { NextRequest } from "next/server"

const MOMA_ROOT = process.env.MOMA_ROOT || path.join(os.homedir(), ".moma")

export const dynamic = "force-dynamic"

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ session_id: string }> }
) {
  const { session_id } = await params
  // Reject anything that isn't a plain id — blocks path traversal (../, encoded slashes, null bytes).
  if (!/^[A-Za-z0-9_-]+$/.test(session_id)) {
    return Response.json({ error: "Invalid session id" }, { status: 400 })
  }
  const rawPath = path.join(MOMA_ROOT, "raw", `${session_id}.jsonl`)
  const sessionPath = path.join(MOMA_ROOT, "sessions", `${session_id}.json`)
  // Defense in depth: ensure resolved paths stay within MOMA_ROOT.
  const root = path.resolve(MOMA_ROOT)
  if (!path.resolve(rawPath).startsWith(root + path.sep) || !path.resolve(sessionPath).startsWith(root + path.sep)) {
    return Response.json({ error: "Invalid session id" }, { status: 400 })
  }

  const observations: unknown[] = []
  if (fs.existsSync(rawPath)) {
    for (const line of fs.readFileSync(rawPath, "utf-8").split("\n").filter(Boolean)) {
      try { observations.push(JSON.parse(line)) } catch {}
    }
  }

  let session = null
  if (fs.existsSync(sessionPath)) {
    try { session = JSON.parse(fs.readFileSync(sessionPath, "utf-8")) } catch {}
  }

  return Response.json({ session, observations })
}
