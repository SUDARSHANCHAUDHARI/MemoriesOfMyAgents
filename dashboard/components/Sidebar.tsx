"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Brain, Clock, Search, Shield, Home, Settings, Radio, Network, Users } from "lucide-react"

const nav = [
  { href: "/", label: "Home", icon: Home },
  { href: "/memories", label: "Memories", icon: Brain },
  { href: "/sessions", label: "Sessions", icon: Clock },
  { href: "/live", label: "Live", icon: Radio },
  { href: "/graph", label: "Graph", icon: Network },
  { href: "/search", label: "Search", icon: Search },
  { href: "/guardlocks", label: "GuardLocks", icon: Shield },
  { href: "/settings", label: "Settings", icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="w-52 shrink-0 border-r border-zinc-800 flex flex-col py-6 px-3 gap-1">
      <div className="px-3 mb-6">
        <span className="text-xs font-bold tracking-widest text-zinc-400 uppercase">moma</span>
      </div>
      {nav.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href !== "/" && pathname.startsWith(href))
        return (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
              active
                ? "bg-zinc-800 text-zinc-100"
                : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
            }`}
          >
            <Icon size={15} />
            {label}
            {label === "Live" && (
              <span className="ml-auto w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            )}
          </Link>
        )
      })}
    </aside>
  )
}
