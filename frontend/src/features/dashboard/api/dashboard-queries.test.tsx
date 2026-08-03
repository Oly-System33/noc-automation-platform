import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { AppProviders } from '@/app/providers'
import { env } from '@/config/env'
import { createQueryClient } from '@/lib/query-client'

import {
  getDashboardSummary,
  getHealth,
  getRecentIncidents,
} from './dashboard-api'
import { dashboardQueryKeys } from './dashboard-query-keys'
import {
  useDashboardSummaryQuery,
  useHealthQuery,
  useRecentIncidentsQuery,
} from './dashboard-queries'

vi.mock('./dashboard-api', () => ({
  getDashboardSummary: vi.fn(),
  getHealth: vi.fn(),
  getRecentIncidents: vi.fn(),
}))

function createWrapper() {
  const client = createQueryClient()
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <AppProviders client={client}>{children}</AppProviders>
  )

  return { client, Wrapper }
}

describe('queries del dashboard', () => {
  it('usa claves deterministas y el retry limitado predeterminado', () => {
    expect(dashboardQueryKeys.health()).toEqual(['dashboard', 'health'])
    expect(dashboardQueryKeys.summary()).toEqual(['dashboard', 'summary'])
    expect(dashboardQueryKeys.incidents(6)).toEqual([
      'dashboard',
      'incidents',
      { limit: 6 },
    ])
    expect(createQueryClient().getDefaultOptions().queries?.retry).toBe(1)
  })

  it('expone resultados, señales y el intervalo configurado', async () => {
    const health = { status: 'ok', database: 'ok' } as const
    const summary = {
      generated_at: '2026-08-03T12:00:00Z',
      counts: {
        active: 0,
        scheduled: 0,
        paused: 0,
        pending_approval: 0,
        executing: 0,
        waiting_confirmation: 0,
        retry_scheduled: 0,
        manual_required: 0,
        stuck: 0,
        failed: 0,
        cancelled: 0,
        closed: 0,
      },
      by_client: {},
      total: 0,
    }
    vi.mocked(getHealth).mockResolvedValue(health)
    vi.mocked(getDashboardSummary).mockResolvedValue(summary)
    const healthContext = createWrapper()
    const summaryContext = createWrapper()

    const healthHook = renderHook(() => useHealthQuery(), {
      wrapper: healthContext.Wrapper,
    })
    const summaryHook = renderHook(() => useDashboardSummaryQuery(), {
      wrapper: summaryContext.Wrapper,
    })

    await waitFor(() => expect(healthHook.result.current.data).toEqual(health))
    await waitFor(() => expect(summaryHook.result.current.data).toEqual(summary))
    expect(vi.mocked(getHealth).mock.calls[0][0]).toBeInstanceOf(AbortSignal)
    expect(vi.mocked(getDashboardSummary).mock.calls[0][0]).toBeInstanceOf(
      AbortSignal,
    )
    const healthQuery = healthContext.client.getQueryCache().find({
      queryKey: dashboardQueryKeys.health(),
    })
    const healthOptions = healthQuery?.options as
      | (NonNullable<typeof healthQuery>['options'] & {
          refetchInterval?: number
        })
      | undefined
    expect(healthOptions?.refetchInterval).toBe(env.pollIntervalMs)
  })

  it('solicita seis incidentes y conserva los anteriores al cambiar límite', async () => {
    const firstPage = {
      items: [],
      total: 6,
      generated_at: '2026-08-03T12:00:00Z',
    }
    vi.mocked(getRecentIncidents).mockImplementation(({ limit }) => {
      if (limit === 6) {
        return Promise.resolve(firstPage)
      }
      return new Promise(() => undefined)
    })
    const { Wrapper } = createWrapper()
    const { result, rerender } = renderHook(
      ({ limit }) => useRecentIncidentsQuery(limit),
      { initialProps: { limit: 6 }, wrapper: Wrapper },
    )

    await waitFor(() => expect(result.current.data).toEqual(firstPage))
    expect(vi.mocked(getRecentIncidents).mock.calls[0][0]).toMatchObject({
      limit: 6,
      signal: expect.any(AbortSignal),
    })

    rerender({ limit: 7 })

    expect(result.current.data).toEqual(firstPage)
    expect(result.current.isPlaceholderData).toBe(true)
  })

  it('expone errores y permite refetch posterior', async () => {
    const failure = new Error('sin conexión')
    const recovered = { status: 'ok', database: 'ok' } as const
    vi.mocked(getHealth).mockRejectedValue(failure)
    const { client, Wrapper } = createWrapper()
    client.setQueryDefaults(dashboardQueryKeys.health(), { retry: false })
    const { result } = renderHook(() => useHealthQuery(), { wrapper: Wrapper })

    await waitFor(() => expect(result.current.error).toBe(failure))
    vi.mocked(getHealth).mockResolvedValue(recovered)

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => expect(result.current.data).toEqual(recovered))
    expect(result.current.error).toBeNull()
  })
})
