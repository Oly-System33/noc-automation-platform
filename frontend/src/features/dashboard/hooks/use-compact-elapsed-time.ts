import { useEffect, useState } from 'react'

import { formatCompactDuration } from '@/features/dashboard/mappers/dashboard-time.mapper'

export function useCompactElapsedTime(timestamp: number) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    setNow(Date.now())
    const timer = window.setInterval(() => setNow(Date.now()), 1_000)

    return () => window.clearInterval(timer)
  }, [timestamp])

  if (timestamp <= 0) {
    return '—'
  }

  return formatCompactDuration((now - timestamp) / 1_000)
}
