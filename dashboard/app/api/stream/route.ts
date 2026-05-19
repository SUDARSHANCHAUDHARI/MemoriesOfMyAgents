import fs from "fs"
import path from "path"
import os from "os"

const MOMA_ROOT = process.env.MOMA_ROOT || path.join(os.homedir(), ".moma")
const RAW_DIR = path.join(MOMA_ROOT, "raw")

export const dynamic = "force-dynamic"

export async function GET() {
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      // Send keep-alive immediately
      controller.enqueue(encoder.encode(": ping\n\n"))

      const seen = new Set<string>()
      let closed = false

      // Track all existing lines first
      const seedExisting = () => {
        if (!fs.existsSync(RAW_DIR)) return
        for (const file of fs.readdirSync(RAW_DIR)) {
          if (!file.endsWith(".jsonl")) continue
          const full = path.join(RAW_DIR, file)
          try {
            const lines = fs.readFileSync(full, "utf-8").split("\n").filter(Boolean)
            for (const line of lines) {
              try { seen.add(JSON.parse(line).id) } catch {}
            }
          } catch {}
        }
      }
      seedExisting()

      const poll = setInterval(() => {
        if (closed) { clearInterval(poll); return }
        if (!fs.existsSync(RAW_DIR)) return
        for (const file of fs.readdirSync(RAW_DIR)) {
          if (!file.endsWith(".jsonl")) continue
          const full = path.join(RAW_DIR, file)
          try {
            const lines = fs.readFileSync(full, "utf-8").split("\n").filter(Boolean)
            for (const line of lines) {
              try {
                const obs = JSON.parse(line)
                if (!seen.has(obs.id)) {
                  seen.add(obs.id)
                  const data = `data: ${JSON.stringify(obs)}\n\n`
                  controller.enqueue(encoder.encode(data))
                }
              } catch {}
            }
          } catch {}
        }
      }, 1500)

      // Keep-alive ping every 20s
      const ping = setInterval(() => {
        if (closed) { clearInterval(ping); return }
        controller.enqueue(encoder.encode(": ping\n\n"))
      }, 20000)

      // Clean up when client disconnects
      return () => {
        closed = true
        clearInterval(poll)
        clearInterval(ping)
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  })
}
