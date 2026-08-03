import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useCompactElapsedTime } from '@/features/dashboard/hooks/use-compact-elapsed-time'

afterEach(() => {
  vi.useRealTimers()
})

describe('useCompactElapsedTime', () => {
  it('actualiza la etiqueta cada segundo sin requests HTTP', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-03T12:00:10Z'))
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const timestamp = new Date('2026-08-03T12:00:00Z').getTime()
    const { result } = renderHook(() => useCompactElapsedTime(timestamp))

    expect(result.current).toBe('10s')

    act(() => {
      vi.advanceTimersByTime(1_000)
    })

    expect(result.current).toBe('11s')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('muestra marcador sin una actualización exitosa', () => {
    const { result } = renderHook(() => useCompactElapsedTime(0))

    expect(result.current).toBe('—')
  })
})
