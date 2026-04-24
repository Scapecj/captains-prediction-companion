'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { CaptainAsciiArt } from '@/components/CaptainAsciiArt'

const getNavigation = () => [
  { name: 'Companion', href: '/companion' },
  { name: 'Dashboard', href: '/dashboard' },
  { name: 'Bot Dash', href: '/bot-dash' },
]

export function Sidebar() {
  const pathname = usePathname()
  const navigation = getNavigation()

  return (
    <div className="fixed inset-y-0 left-0 z-40 flex w-48 flex-col border-r border-cyan/15 bg-[linear-gradient(180deg,rgba(10,14,22,0.98),rgba(6,8,12,0.98))] shadow-[inset_0_1px_0_rgba(255,255,255,0.03),0_0_30px_rgba(0,0,0,0.5)]">
      {/* Brand */}
      <div className="border-b border-cyan/10 px-3 py-4 space-y-3 bg-[linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0))]">
        <Link href="/companion" className="block group px-1">
          <span className="text-base font-semibold tracking-tight text-text-primary group-hover:text-cyan transition-colors">
            Captains Prediction Companion
          </span>
          <p className="text-[10px] text-text-muted mt-0.5">
            Kalshi market analysis
          </p>
        </Link>
        <CaptainAsciiArt variant="sidebar" className="scale-[0.72] origin-left" />
        <div className="max-w-[150px] rounded-xl border border-cyan/20 bg-[linear-gradient(180deg,rgba(34,211,238,0.08),rgba(0,0,0,0.35))] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
          <CaptainAsciiArt variant="wordmark" className="scale-[0.42] origin-left" />
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          const isExternal = 'external' in item && item.external

          if (isExternal) {
            return (
              <a
                key={item.name}
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between px-3 py-2 rounded text-sm transition-colors text-text-secondary hover:text-text-primary hover:bg-surface-hover"
              >
                {item.name}
                <span className="text-[10px] text-text-muted">↗</span>
              </a>
            )
          }

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                block px-3 py-2 rounded text-sm transition-colors
                ${
                  isActive
                    ? 'bg-surface-elevated text-text-primary border-l-2 border-cyan -ml-px pl-[11px]'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                }
              `}
            >
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald" />
            <span className="text-xs text-text-muted">Live</span>
          </div>
          <span className="text-[10px] text-text-muted font-mono">v1.0</span>
        </div>
      </div>
    </div>
  )
}
