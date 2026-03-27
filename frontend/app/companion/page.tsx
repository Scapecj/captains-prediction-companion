import { EventMarketPlanner } from '@/components/terminal/EventMarketPlanner'

export default function CompanionPage() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6">
      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface p-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.14),transparent_42%)]" />
        <div className="relative">
          <div className="text-[10px] uppercase tracking-[0.24em] text-cyan">
            Captains Prediction Companion
          </div>
          <h1 className="mt-3 font-display text-4xl leading-none text-text-primary">
            Deterministic Kalshi market cards
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-text-secondary">
            This page renders the MCP market card directly. Paste a Kalshi board
            URL to load the event, then drill into a phrase contract without
            letting the chat layer rewrite the output into prose.
          </p>
        </div>
      </header>

      <EventMarketPlanner />
    </div>
  )
}
