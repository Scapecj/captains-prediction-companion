import { DashboardPage as DashboardSurface } from './DashboardPage'
import { CaptainAsciiArt } from '@/components/CaptainAsciiArt'

export default function DashboardRoute() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6">
      <div className="rounded-2xl border border-border bg-[linear-gradient(180deg,rgba(16,17,21,0.98),rgba(10,10,14,0.94))] p-5 space-y-4 shadow-[0_18px_60px_rgba(0,0,0,0.28)]">
        <CaptainAsciiArt variant="wordmark" />
        <CaptainAsciiArt variant="dashboard" />
      </div>
      <DashboardSurface />
    </div>
  )
}
