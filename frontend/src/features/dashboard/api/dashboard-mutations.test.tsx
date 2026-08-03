import { act, renderHook } from '@testing-library/react'
import type { QueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { AppProviders } from '@/app/providers'
import { createQueryClient } from '@/lib/query-client'

import {
  approveScheduledAction,
  pauseScheduledAction,
  rejectScheduledAction,
  resumeScheduledAction,
  retryIntervention,
} from './dashboard-api'
import {
  useApproveScheduledActionMutation,
  usePauseScheduledActionMutation,
  useRejectScheduledActionMutation,
  useResumeScheduledActionMutation,
  useRetryInterventionMutation,
} from './dashboard-mutations'
import { dashboardQueryKeys } from './dashboard-query-keys'

vi.mock('./dashboard-api', () => ({
  approveScheduledAction: vi.fn(),
  pauseScheduledAction: vi.fn(),
  rejectScheduledAction: vi.fn(),
  resumeScheduledAction: vi.fn(),
  retryIntervention: vi.fn(),
}))

function createWrapper() {
  const client = createQueryClient()
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <AppProviders client={client}>{children}</AppProviders>
  )
  vi.spyOn(client, 'invalidateQueries').mockResolvedValue()

  return { client, Wrapper }
}

function invalidatedKeys(client: QueryClient) {
  return vi.mocked(client.invalidateQueries).mock.calls.map(([filters]) => filters?.queryKey)
}

const operationRefreshKeys = [
  dashboardQueryKeys.operationLists(),
  dashboardQueryKeys.summary(),
  dashboardQueryKeys.incidentLists(),
  dashboardQueryKeys.interventionLists(),
]

describe('mutaciones del dashboard', () => {
  it.each([
    ['pause', usePauseScheduledActionMutation, pauseScheduledAction],
    ['resume', useResumeScheduledActionMutation, resumeScheduledAction],
  ] as const)('ejecuta %s sin retry e invalida operaciones relacionadas', async (_name, hook, api) => {
    vi.mocked(api).mockResolvedValue({
      success: true,
      scheduled_action_id: 4,
      state: 'processing',
      execution_started: true,
    })
    const { client, Wrapper } = createWrapper()
    const { result } = renderHook(() => hook(), { wrapper: Wrapper })

    await act(async () => {
      await result.current.mutateAsync({ scheduledActionId: 4 })
    })

    expect(api).toHaveBeenCalledWith({ scheduledActionId: 4 })
    expect(result.current.failureCount).toBe(0)
    expect(invalidatedKeys(client)).toEqual(operationRefreshKeys)
    expect(invalidatedKeys(client)).not.toContainEqual(dashboardQueryKeys.health())
  })

  it.each([
    ['approve', useApproveScheduledActionMutation, approveScheduledAction],
    ['reject', useRejectScheduledActionMutation, rejectScheduledAction],
  ] as const)('ejecuta %s e incluye aprobaciones en la invalidación', async (_name, hook, api) => {
    vi.mocked(api).mockResolvedValue({
      success: true,
      scheduled_action_id: 7,
      previous_state: 'pending_approval',
      state: 'processing',
      execution_started: true,
      approved: true,
      rejected: true,
    })
    const { client, Wrapper } = createWrapper()
    const { result } = renderHook(() => hook(), { wrapper: Wrapper })

    await act(async () => {
      await result.current.mutateAsync({ scheduledActionId: 7, note: 'checked' })
    })

    expect(api).toHaveBeenCalledWith({ scheduledActionId: 7, note: 'checked' })
    expect(invalidatedKeys(client)).toEqual([
      ...operationRefreshKeys,
      dashboardQueryKeys.approvalLists(),
    ])
  })

  it('retry invalida listas operativas sin health ni runbooks', async () => {
    vi.mocked(retryIntervention).mockResolvedValue({
      success: true,
      intervention_id: 'call_flow:8',
      retry_started: true,
    })
    const { client, Wrapper } = createWrapper()
    const { result } = renderHook(() => useRetryInterventionMutation(), {
      wrapper: Wrapper,
    })

    await act(async () => {
      await result.current.mutateAsync({ interventionId: 'call_flow:8' })
    })

    expect(invalidatedKeys(client)).toEqual([
      dashboardQueryKeys.interventionLists(),
      dashboardQueryKeys.operationLists(),
      dashboardQueryKeys.incidentLists(),
      dashboardQueryKeys.summary(),
    ])
    expect(invalidatedKeys(client)).not.toContainEqual(dashboardQueryKeys.health())
    expect(invalidatedKeys(client)).not.toContainEqual(dashboardQueryKeys.runbook('call_flow:8'))
  })
})
