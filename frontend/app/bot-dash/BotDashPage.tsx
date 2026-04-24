'use client'

import { useEffect, useState } from 'react'
import { apiGet, apiJson } from '@/lib/captainlabs-api'
import type { BotAction, BotListItem, BotOverview, BotStatusSnapshot, Position } from '@/types/captainlabs'
import type { ReactNode } from 'react'

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${value >= 0 ? '+' : ''}$${Math.abs(Number(value)).toFixed(2)}`
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${value >= 0 ? '+' : ''}${Number(value).toFixed(1)}%`
}

function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' }) {
  const tones = {
    neutral: 'bg-border text-text-secondary',
    good: 'bg-emerald/15 text-emerald',
    warn: 'bg-amber-500/15 text-amber-400',
    bad: 'bg-rose/15 text-rose',
  }
  return <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${tones[tone]}`}>{children}</span>
}

export function BotDashPage() {
  const [bots, setBots] = useState<BotListItem[]>([])
  const [activeBot, setActiveBot] = useState<BotOverview | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [actions, setActions] = useState<BotAction[]>([])
  const [performance, setPerformance] = useState<Record<string, unknown> | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  async function loadBot(botId: string) {
    const overview = await apiGet<BotOverview>(`/bots/${botId}`)
    const status = await apiGet<{ status: BotStatusSnapshot }>(`/bots/${botId}/status`)
    const positionsRes = await apiGet<{ positions: Position[] }>(`/bots/${botId}/positions`)
    const actionsRes = await apiGet<{ actions: BotAction[] }>(`/bots/${botId}/actions`)
    const perfRes = await apiGet<{ performance: Record<string, unknown> }>(`/bots/${botId}/performance`)
    const logsRes = await apiGet<{ logs: string[] }>(`/bots/${botId}/logs`)

    const statusSnapshot = status.status ?? null
    setActiveBot({
      ...overview,
      status: statusSnapshot ?? overview.status,
    })
    setPositions(positionsRes.positions ?? [])
    setActions(actionsRes.actions ?? [])
    setPerformance(perfRes.performance ?? null)
    setLogs(logsRes.logs ?? [])
  }

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const botList = await apiGet<{ bots: BotListItem[] }>('/bots')
        if (!alive) return
        setBots(botList.bots ?? [])
        if ((botList.bots ?? []).length > 0) {
          await loadBot(botList.bots[0].id)
        }
      } catch (err) {
        if (!alive) return
        setError(err instanceof Error ? err.message : 'Unable to load bot dash')
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [])

  async function refreshCurrent() {
    if (!activeBot) return
    await loadBot(activeBot.bot.id)
  }

  async function toggleBot(nextAction: 'start' | 'stop') {
    if (!activeBot) return
    await apiJson(`/bots/${activeBot.bot.id}/${nextAction}`, { method: 'POST', body: '{}' })
    await refreshCurrent()
    const botList = await apiGet<{ bots: BotListItem[] }>('/bots')
    setBots(botList.bots ?? [])
  }

  const bot = activeBot?.bot
  const status = activeBot?.status
  const statusLabel = String(status?.status ?? bot?.status ?? '--')
  const performanceSnapshot = performance as Record<string, unknown> | null

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6">
      <header className="rounded-2xl border border-border bg-surface p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.24em] text-cyan">Bot Dash</div>
            <h1 className="mt-3 font-display text-4xl leading-none text-text-primary">Automation layer</h1>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-text-secondary">
              This surface shows bot status, positions, actions, performance, and logs. The frontend only talks to the CaptainLabs bot API, not the simmer internals.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {bots.map((item) => (
              <button
                key={item.id}
                onClick={() => loadBot(item.id)}
                className={`rounded-full border px-3 py-1 text-xs ${bot?.id === item.id ? 'border-cyan bg-cyan/10 text-text-primary' : 'border-border text-text-secondary'}`}
              >
                {item.name}
              </button>
            ))}
          </div>
        </div>
      </header>

      {error ? <div className="rounded-xl border border-rose/30 bg-rose/10 p-4 text-sm text-rose">{error}</div> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Status" value={statusLabel} pill={<Pill tone={statusLabel === 'active' ? 'good' : statusLabel === 'paused' ? 'warn' : 'bad'}>{statusLabel}</Pill>} />
        <Card title="Strategy" value={status?.strategyLabel ?? bot?.strategyLabel ?? '--'} />
        <Card title="Last action" value={String(status?.lastAction ?? '--')} />
        <Card title="Last update" value={String(status?.lastUpdate ?? '--')} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <div className="rounded-2xl border border-border bg-surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary">Active positions</h2>
            <span className="text-xs text-text-muted">{positions.length} open</span>
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
                  <th className="px-4 py-3">PnL $</th>
                  <th className="px-4 py-3">PnL %</th>
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
                    <td className="px-4 py-3">{formatCurrency(position.pnlDollars)}</td>
                    <td className="px-4 py-3">{formatPercent(position.pnlPercent)}</td>
                    <td className="px-4 py-3"><Pill>{position.status}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-border bg-surface p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-text-primary">Recent actions</h2>
              <span className="text-xs text-text-muted">{actions.length} entries</span>
            </div>
            <div className="space-y-2 text-sm">
              {actions.map((action) => (
                <div key={action.id} className="rounded-xl border border-border bg-surface-elevated p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-text-primary">{action.type}</span>
                    <span className="text-xs text-text-muted">{action.timestamp}</span>
                  </div>
                  <div className="mt-1 text-text-secondary">{action.market}</div>
                  <div className="mt-1 text-xs text-text-muted">
                    {action.quantity} @ {action.price ?? '--'} — {action.reason ?? 'No reason'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <h2 className="mb-4 text-lg font-semibold text-text-primary">Performance snapshot</h2>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Metric label="Total PnL" value={formatCurrency(Number(performanceSnapshot?.totalPnl ?? 0))} />
              <Metric label="Today PnL" value={formatCurrency(Number(performanceSnapshot?.todayPnl ?? 0))} />
              <Metric label="Win rate" value={formatPercent(Number(performanceSnapshot?.winRate ?? 0))} />
              <Metric label="Trades today" value={String(performanceSnapshot?.tradesToday ?? '--')} />
              <Metric label="Open positions" value={String(performanceSnapshot?.openPositions ?? '--')} />
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5">
            <details>
              <summary className="cursor-pointer text-lg font-semibold text-text-primary">Logs</summary>
              <div className="mt-4 max-h-72 overflow-auto rounded-xl border border-border bg-black/30 p-3 text-xs text-text-secondary">
                {logs.map((line, index) => (
                  <div key={`${line}-${index}`} className="whitespace-pre-wrap border-b border-border/40 py-1 last:border-0">
                    {line}
                  </div>
                ))}
              </div>
            </details>
          </div>
        </div>
      </section>

      <section className="flex items-center gap-3">
        <button
          onClick={() => toggleBot('start')}
          className="rounded-full border border-emerald/40 bg-emerald/10 px-4 py-2 text-sm text-emerald shadow-[0_0_18px_rgba(16,185,129,0.08)] transition-colors hover:bg-emerald/15"
        >
          Start
        </button>
        <button
          onClick={() => toggleBot('stop')}
          className="rounded-full border border-rose/40 bg-rose/10 px-4 py-2 text-sm text-rose shadow-[0_0_18px_rgba(244,63,94,0.08)] transition-colors hover:bg-rose/15"
        >
          Stop
        </button>
      </section>
    </div>
  )
}

function Card({ title, value, pill }: { title: string; value: string; pill?: ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">{title}</div>
        {pill}
      </div>
      <div className="mt-2 text-base text-text-primary">{value}</div>
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
