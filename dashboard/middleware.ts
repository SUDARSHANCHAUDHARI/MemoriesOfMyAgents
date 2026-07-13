import { NextRequest, NextResponse } from "next/server"

// Opt-in auth gate for the dashboard's API routes, which expose local agent
// memory/session data. If DASHBOARD_TOKEN is set, every /api/* request must
// present it (Bearer header or `dash_token` cookie). Unset => localhost-only dev
// behaviour is preserved. Set it whenever the dashboard is reachable off-host.
const TOKEN = process.env.DASHBOARD_TOKEN || ""

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return diff === 0
}

export function middleware(req: NextRequest) {
  if (!TOKEN) return NextResponse.next()

  const auth = req.headers.get("authorization") || ""
  const bearer = auth.toLowerCase().startsWith("bearer ") ? auth.slice(7) : ""
  const cookie = req.cookies.get("dash_token")?.value || ""
  const presented = bearer || cookie

  if (!presented || !timingSafeEqual(presented, TOKEN)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  return NextResponse.next()
}

export const config = {
  matcher: ["/api/:path*"],
}
