/**
 * Time formatting utilities for pipeline status and relative timestamps.
 */

/**
 * Formats elapsed seconds into human-readable duration.
 * @example formatElapsed(45.2) => "45.2s"
 * @example formatElapsed(125) => "2m 5s"
 */
export function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}m ${secs}s`
}

/**
 * Formats ISO timestamp to relative time string.
 * @example formatTime("2024-01-15T10:30:00Z") => "5m ago"
 * @example formatTime(null) => "—"
 */
export function formatTime(isoString: string | null): string {
  if (!isoString) return '—'
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
