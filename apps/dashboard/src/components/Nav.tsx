"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { Activity, FlaskConical, GitCompare, TerminalSquare, Zap } from "lucide-react";

const links = [
  { href: "/playground", label: "Playground", icon: TerminalSquare },
  { href: "/benchmarks", label: "Benchmarks", icon: FlaskConical },
  { href: "/requests", label: "Requests", icon: Activity },
  { href: "/compare", label: "Compare", icon: GitCompare },
];

export function Nav() {
  const path = usePathname();

  return (
    <nav className="flex items-center gap-1 px-4 py-3 border-b border-zinc-800 bg-zinc-950">
      <Link href="/" className="flex items-center gap-2 mr-6">
        <Zap className="w-4 h-4 text-sky-400" />
        <span className="text-sm font-semibold tracking-widest text-zinc-100">INFERX</span>
      </Link>

      {links.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          className={clsx(
            "flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors",
            path.startsWith(href)
              ? "bg-zinc-800 text-zinc-100"
              : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900",
          )}
        >
          <Icon className="w-3.5 h-3.5" />
          {label}
        </Link>
      ))}
    </nav>
  );
}
