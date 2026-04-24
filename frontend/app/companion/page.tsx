import { EventMarketPlanner } from '@/components/terminal/EventMarketPlanner'
import { CaptainAsciiArt } from '@/components/CaptainAsciiArt'

export default function CompanionPage() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6">
      <header className="relative overflow-hidden rounded-2xl border border-border bg-[linear-gradient(180deg,rgba(16,17,21,0.98),rgba(10,10,14,0.96))] p-6 shadow-[0_18px_60px_rgba(0,0,0,0.35)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.14),transparent_42%)]" />
        <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-cyan via-emerald to-rose opacity-60" />
        <div className="relative grid gap-8 xl:grid-cols-[1.15fr_auto] xl:items-start">
          <div>
            <div className="text-[10px] uppercase tracking-[0.24em] text-cyan animate-captain-flicker">
              Captains Prediction Companion
            </div>
            <h1 className="mt-3 max-w-[16ch] font-display text-[2.65rem] leading-[0.98] text-text-primary xl:text-[2.9rem]">
              Decision layer for market analysis
            </h1>
            <p className="mt-5 max-w-3xl text-sm leading-6 text-text-secondary">
              Companion stays focused on market interpretation and contract selection.
              Dashboard is for account state. Bot Dash is for automation. This surface remains the
              place to analyze a board or contract before a trade decision is made.
            </p>
          </div>
          <div className="flex justify-start xl:justify-end">
            <div className="space-y-3">
              <CaptainAsciiArt variant="wordmark" />
              <CaptainAsciiArt variant="hero" className="xl:scale-[0.92] xl:origin-top-right" />
            </div>
          </div>
        </div>
      </header>

      <EventMarketPlanner />
    </div>
  )
}
