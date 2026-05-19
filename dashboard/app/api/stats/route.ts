import { NextResponse } from "next/server"
import { getStats } from "@/lib/moma"

export async function GET() {
  return NextResponse.json(getStats())
}
