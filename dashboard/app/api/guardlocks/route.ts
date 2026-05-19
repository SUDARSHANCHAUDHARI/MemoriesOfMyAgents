import { NextResponse } from "next/server"
import { getGuardLocks, getConflicts } from "@/lib/moma"

export async function GET() {
  return NextResponse.json({
    guardlocks: getGuardLocks(),
    conflicts: getConflicts(),
  })
}
