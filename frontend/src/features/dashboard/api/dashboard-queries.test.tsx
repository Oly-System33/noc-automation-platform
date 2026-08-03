import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { AppProviders } from '@/app/providers'
import { env } from '@/config/env'
import { createQueryClient } from '@/lib/query-client'

import {
  getDashboardApprovals,
  getDashboardInterventions,
  getDashboardOperations,
  getDashboardSummary,
  getHealth,
  getInterventionRunbook,
  getRecentIncidents,
} from './dashboard-api'
import { dashboardQueryKeys } from './dashboard-query-keys'
import {
  useDashboardApprovalsQuery,
  useDashboardInterventionsQuery,
  useDashboardOperationsQuery,
  useDashboardSummaryQuery,
  useHealthQuery,
  useInterventionRunbookQuery,
  useRecentIncidentsQuery,
} from './dashboard-queries'

vi.mock('./dashboard-api', () => ({
  getDashboardApprovals: vi.fn(),
  getDashboardInterventions: vi.fn(),
  getDashboardOperations: vi.fn(),
  getDashboardSummary: vi.fn(),
  getHealth: vi.fn(),
  getInterventionRunbook: vi.fn(),
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
    expect(dashboardQueryKeys.incidentLists()).toEqual(['dashboard', 'incidents'])
    expect(dashboardQueryKeys.operations(5, true)).toEqual([
      'dashboard',
      'operations',
      { limit: 5, activeOnly: true },
    ])
    expect(dashboardQueryKeys.approvals(3)).toEqual([
      'dashboard',
      'approvals',
      { limit: 3 },
    ])
    expect(dashboardQueryKeys.interventions(3)).toEqual([
      'dashboard',
      'interventions',
      { limit: 3 },
    ])
    expect(dashboardQueryKeys.runbook('item:1')).toEqual([
      'dashboard',
      'runbooks',
      'item:1',
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
      limit: 6,
      offset: 0,
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

  it('aplica polling, señales y límites predeterminados a las listas F4', async () => {
    const response = { items: [], total: 0, limit: 3, offset: 0, generated_at: '2026-08-03T12:00:00Z' }
    vi.mocked(getDashboardOperations).mockResolvedValue(response)
    vi.mocked(getDashboardApprovals).mockResolvedValue(response)
    vi.mocked(getDashboardInterventions).mockResolvedValue(response)
    const contexts = [createWrapper(), createWrapper(), createWrapper()]

    renderHook(() => useDashboardOperationsQuery(), { wrapper: contexts[0].Wrapper })
    renderHook(() => useDashboardApprovalsQuery(), { wrapper: contexts[1].Wrapper })
    renderHook(() => useDashboardInterventionsQuery(), { wrapper: contexts[2].Wrapper })

    await waitFor(() => expect(getDashboardInterventions).toHaveBeenCalled())
    expect(vi.mocked(getDashboardOperations).mock.calls[0][0]).toMatchObject({
      limit: 5,
      activeOnly: true,
      signal: expect.any(AbortSignal),
    })
    expect(vi.mocked(getDashboardApprovals).mock.calls[0][0]).toMatchObject({
      limit: 3,
      signal: expect.any(AbortSignal),
    })
    expect(vi.mocked(getDashboardInterventions).mock.calls[0][0]).toMatchObject({
      limit: 3,
      signal: expect.any(AbortSignal),
    })
    for (const [context, key] of [
      [contexts[0], dashboardQueryKeys.operations(5, true)],
      [contexts[1], dashboardQueryKeys.approvals(3)],
      [contexts[2], dashboardQueryKeys.interventions(3)],
    ] as const) {
      const query = context.client.getQueryCache().find({ queryKey: key })
      const options = query?.options as
        | (NonNullable<typeof query>['options'] & { refetchInterval?: number })
        | undefined
      expect(options?.refetchInterval).toBe(env.pollIntervalMs)
    }
  })

  it('mantiene el runbook deshabilitado y no configura polling', async () => {
    const runbook = {
      intervention_id: 'call_flow:2',
      source: 'current_runbook' as const,
      warning: null,
      actions: ['email'],
      target: null,
      delay_minutes: null,
      execution_mode: null,
      approval_when: null,
      pre_actions: [],
      pre_target: null,
    }
    vi.mocked(getInterventionRunbook).mockResolvedValue(runbook)
    const { client, Wrapper } = createWrapper()
    const { result, rerender } = renderHook(
      ({ enabled }) => useInterventionRunbookQuery('call_flow:2', enabled),
      { initialProps: { enabled: false }, wrapper: Wrapper },
    )

    expect(result.current.fetchStatus).toBe('idle')
    expect(getInterventionRunbook).not.toHaveBeenCalled()
    const query = client.getQueryCache().find({
      queryKey: dashboardQueryKeys.runbook('call_flow:2'),
    })
    const options = query?.options as
      | (NonNullable<typeof query>['options'] & { refetchInterval?: number })
      | undefined
    expect(options?.refetchInterval).toBeUndefined()

    rerender({ enabled: true })
    await waitFor(() => expect(result.current.data).toEqual(runbook))
    expect(vi.mocked(getInterventionRunbook).mock.calls[0]).toEqual([
      'call_flow:2',
      expect.any(AbortSignal),
    ])
  })
})
