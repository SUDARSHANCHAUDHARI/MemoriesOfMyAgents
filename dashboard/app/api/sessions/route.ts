import { NextResponse } from "next/server"
import { getAllSessions } from "@/lib/moma"

export async function GET() {
  return NextResponse.json(getAllSessions())
}
