'use client'

import { useEffect, useState } from 'react'
import { apiGet } from '@/lib/captainlabs-api'
import type {
  DashboardPerformance,
  DashboardSummary,
  Position,
  Wallet,
} from '@/types/captainlabs'

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${value >= 0 ? '+' : ''}$${Math.abs(Number(value)).toFixed(2)}`
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${value >= 0 ? '+' : ''}${Number(value).toFixed(1)}%`
}

function StatusPill({ value }: { value: string | null | undefined }) {
  const tone =
    value === 'active'
      ? 'bg-emerald/15 text-emerald border-emerald/30'
      : value === 'paused'
        ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
        : 'bg-border text-text-secondary border-border'
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] ${tone}`}>
      {value ?? '--'}
    </span>
  )
}

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [activity, setActivity] = useState<Array<Record<string, unknown>>>([])
  const [performance, setPerformance] = useState<DashboardPerformance | null>(null)
  const [wallets, setWallets] = useState<Array<Wallet & { positionCount?: number }>>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const [summaryRes, positionsRes, activityRes, performanceRes, walletsRes] = await Promise.all([
          apiGet<DashboardSummary>('/dashboard/summary'),
          apiGet<{ positions: Position[] }>('/dashboard/positions'),
          apiGet<{ activity: Array<Record<string, unknown>> }>('/dashboard/activity'),
          apiGet<{ performance: DashboardPerformance }>('/dashboard/performance'),
          apiGet<{ wallets: Wallet[] }>('/dashboard/wallets'),
        ])
        if (!alive) return
        setSummary(summaryRes)
        setPositions(positionsRes.positions ?? [])
        setActivity(activityRes.activity ?? [])
        setPerformance(performanceRes.performance ?? null)
        setWallets(walletsRes.wallets ?? [])
      } catch (err) {
        if (!alive) return
        setError(err instanceof Error ? err.message : 'Unable to load dashboard')
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [])

  const metrics = summary?.summary
  const userPerformance = performance?.user

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6">
      <header className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.24em] text-cyan">Dashboard</div>
            <h1 className="mt-3 font-display text-4xl leading-none text-text-primary">User state layer</h1>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-text-secondary">
              Positions, activity, performance, and wallets live here. This is the multi-user account surface for tracking the state of the trading companion.
            </p>
          </div>
          {summary?.user?.profile?.name ? (
            <div className="rounded-xl border border-border bg-surface-elevated px-4 py-3 text-sm text-text-secondary">
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">Signed in</div>
              <div className="mt-1 text-text-primary">{summary.user.profile.name}</div>
            </div>
          ) : null}
        </div>
      </header>

      {error ? <div className="rounded-xl border border-rose/30 bg-rose/10 p-4 text-sm text-rose">{error}</div> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ['Wallets', metrics?.walletCount ?? 0],
          ['Bots', metrics?.botCount ?? 0],
          ['Open positions', metrics?.openPositions ?? 0],
          ['Today PnL', formatCurrency(metrics?.todayPnl ?? null)],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-xl border border-border bg-surface p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">{label}</div>
            <div className="mt-2 text-2xl font-semibold text-text-primary">{value as string | number}</div>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <div className="rounded-2xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary">Positions</h2>
            <span className="text-xs text-text-muted">{positions.length} total</span>
          </div>
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-surface-elevated text-xs uppercase tracking-[0.18em] text-text-muted">
                <tr>
                  <th className="px-4 py-3">Market</th>
                  <th className="px-4 py-3">Side</th>
                  <th className="px-4 py-3">Entry</th>
                  <th className="px-4 py-3">Current</th>
                  <th className="px-4 py-3">Qty</th>
                  <th className="px-4 py-3">PnL</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => (
                  <tr key={position.id} className="border-t border-border">
                    <td className="px-4 py-3 text-text-primary">{position.market}</td>
                    <td className="px-4 py-3 uppercase text-text-secondary">{position.side}</td>
                    <td className="px-4 py-3">{position.entryPrice.toFixed(2)}</td>
                    <td className="px-4 py-3">{position.currentPrice.toFixed(2)}</td>
                    <td className="px-4 py-3">{position.quantity}</td>
                    <td className="px-4 py-3">
                      <div className="text-text-primary">{formatCurrency(position.pnlDollars)}</div>
                      <div className="text-xs text-text-muted">{formatPercent(position.pnlPercent)}</div>
                    </td>
                    <td className="px-4 py-3"><StatusPill value={position.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <h2 className="mb-4 text-lg font-semibold text-text-primary">Performance</h2>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Metric label="Total PnL" value={formatCurrency(userPerformance?.totalPnl)} />
              <Metric label="Today PnL" value={formatCurrency(userPerformance?.todayPnl)} />
              <Metric label="Win rate" value={formatPercent(userPerformance?.winRate)} />
              <Metric label="Trades today" value={String(userPerformance?.tradesToday ?? '--')} />
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <h2 className="mb-4 text-lg font-semibold text-text-primary">Wallets</h2>
            <div className="space-y-3">
              {wallets.map((wallet) => (
                <div key={wallet.id} className="rounded-xl border border-border bg-surface-elevated p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-text-primary">{wallet.label}</div>
                      <div className="text-xs text-text-muted">{wallet.chain}</div>
                    </div>
                    <div className="text-right text-xs text-text-muted">
                      <div>{wallet.address}</div>
                      <div>{wallet.positionCount ?? 0} positions</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-5">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Activity</h2>
        <div className="space-y-2 text-sm">
          {activity.map((item) => (
            <div key={String(item.id ?? `${item.timestamp}`)} className="rounded-xl border border-border bg-surface-elevated p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-text-primary">{String(item.type ?? 'activity')}</span>
                <span className="text-xs text-text-muted">{String(item.timestamp ?? '')}</span>
              </div>
              <div className="mt-1 text-text-secondary">{String(item.reason ?? item.summary ?? '')}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-elevated p-3">
      <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">{label}</div>
      <div className="mt-2 text-base font-medium text-text-primary">{value}</div>
    </div>
  )
}
