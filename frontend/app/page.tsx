'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { CaptainAsciiArt } from '@/components/CaptainAsciiArt'

export default function HomePage() {
  const router = useRouter()

  useEffect(() => {
    const timer = window.setTimeout(() => {
      router.replace('/companion')
    }, 900)
    return () => window.clearTimeout(timer)
  }, [router])

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col items-center justify-center gap-6 px-4 text-center">
      <CaptainAsciiArt variant="home" />
      <CaptainAsciiArt variant="wordmark" className="max-w-4xl" />
      <div className="max-w-2xl text-sm leading-6 text-text-secondary">
        Captains Prediction Companion is loading the Companion surface. Black flag mode engaged.
      </div>
      <button
        type="button"
        onClick={() => router.replace('/companion')}
        className="rounded-full border border-cyan/40 bg-cyan/10 px-5 py-2 text-sm text-cyan transition-colors hover:bg-cyan/15"
      >
        Enter the Companion deck
      </button>
    </div>
  )
}
