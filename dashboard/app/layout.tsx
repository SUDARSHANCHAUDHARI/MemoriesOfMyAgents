import type { Metadata } from "next"
import { Geist_Mono } from "next/font/google"
import "./globals.css"
import Sidebar from "@/components/Sidebar"

const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" })

export const metadata: Metadata = {
  title: "MemoriesOfMyAgents",
  description: "Local-first memory layer for AI coding agents",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${mono.variable} h-full`}>
      <body className="font-mono bg-zinc-950 text-zinc-100 antialiased h-full">
        <div className="flex h-full overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </body>
    </html>
  )
}
