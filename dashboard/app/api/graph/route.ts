import fs from "fs"
import path from "path"
import os from "os"

const MOMA_ROOT = process.env.MOMA_ROOT || path.join(os.homedir(), ".moma")
const GRAPH_PATH = path.join(MOMA_ROOT, "graph", "graph.json")

export const dynamic = "force-dynamic"

export async function GET() {
  if (!fs.existsSync(GRAPH_PATH)) {
    return Response.json({ nodes: [], edges: [] })
  }
  try {
    const data = JSON.parse(fs.readFileSync(GRAPH_PATH, "utf-8"))
    return Response.json(data)
  } catch {
    return Response.json({ nodes: [], edges: [] })
  }
}
