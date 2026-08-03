const DASH = '—'

export function formatCompactDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.floor(totalSeconds))

  if (seconds < 60) {
    return `${seconds}s`
  }

  if (seconds < 3_600) {
    return `${Math.floor(seconds / 60)}m`
  }

  if (seconds < 86_400) {
    return `${Math.floor(seconds / 3_600)}h`
  }

  return `${Math.floor(seconds / 86_400)}d`
}

export function formatCompactAge(
  timestamp: string | null | undefined,
  referenceTimestamp: string | number | Date = Date.now(),
) {
  if (!timestamp) {
    return DASH
  }

  const startedAt = new Date(timestamp).getTime()
  const reference = new Date(referenceTimestamp).getTime()

  if (!Number.isFinite(startedAt) || !Number.isFinite(reference)) {
    return DASH
  }

  return formatCompactDuration((reference - startedAt) / 1_000)
}

export function formatPollingInterval(milliseconds: number) {
  if (milliseconds < 60_000) {
    return `${Math.max(1, Math.round(milliseconds / 1_000))}s`
  }

  return `${Math.max(1, Math.round(milliseconds / 60_000))}m`
}
