import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api-client'

import {
  approveScheduledAction,
  getDashboardApprovals,
  getDashboardInterventions,
  getDashboardOperations,
  getDashboardSummary,
  getHealth,
  getInterventionRunbook,
  getRecentIncidents,
  pauseScheduledAction,
  rejectScheduledAction,
  resumeScheduledAction,
  retryIntervention,
} from './dashboard-api'
import type { DashboardStatusCounts } from './dashboard-api.types'

const counts: DashboardStatusCounts = {
  active: 1,
  scheduled: 2,
  paused: 3,
  pending_approval: 4,
  executing: 5,
  waiting_confirmation: 6,
  retry_scheduled: 7,
  manual_required: 8,
  stuck: 9,
  failed: 10,
  cancelled: 11,
  closed: 12,
}

describe('API del dashboard', () => {
  it('obtiene health y conserva la respuesta real de base no disponible', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'ok', database: 'ok' })),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ status: 'error', database: 'unavailable' }),
          { status: 503 },
        ),
      )
    vi.stubGlobal('fetch', fetchMock)

    await expect(getHealth()).resolves.toEqual({ status: 'ok', database: 'ok' })
    await expect(getHealth()).resolves.toEqual({
      status: 'error',
      database: 'unavailable',
    })
  })

  it('propaga un 503 que no cumple el contrato de health', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: 'maintenance' }), { status: 503 }),
        ),
    )

    await expect(getHealth()).rejects.toBeInstanceOf(ApiError)
  })

  it('consulta resumen e incidentes recientes con limit=6 y señales', async () => {
    const summary = {
      generated_at: '2026-08-03T12:00:00Z',
      counts,
      by_client: { ACME: 3 },
      total: 3,
    }
    const incidents = {
      items: [],
      total: 0,
      generated_at: '2026-08-03T12:00:00Z',
    }
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify(summary)))
      .mockResolvedValueOnce(new Response(JSON.stringify(incidents)))
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()

    await expect(getDashboardSummary(controller.signal)).resolves.toEqual(summary)
    await expect(
      getRecentIncidents({ limit: 6, signal: controller.signal }),
    ).resolves.toEqual(incidents)

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/api/dashboard/summary',
      'http://localhost:8000/api/incidents?limit=6',
    ])
    expect(fetchMock.mock.calls.every(([, options]) => options?.signal === controller.signal)).toBe(
      true,
    )
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('operations'))).toBe(false)
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('approvals'))).toBe(false)
  })

  it('consulta operaciones, aprobaciones, intervenciones y runbook con sus parámetros', async () => {
    const response = { items: [], total: 0, generated_at: '2026-08-03T12:00:00Z' }
    const runbook = {
      intervention_id: 'scheduled_action:4',
      source: 'persisted_action_plan' as const,
      warning: null,
      actions: ['telegram'],
      target: 'noc',
      delay_minutes: null,
      execution_mode: 'delayed',
      approval_when: null,
      pre_actions: [],
      pre_target: null,
    }
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify(response)))
      .mockResolvedValueOnce(new Response(JSON.stringify(response)))
      .mockResolvedValueOnce(new Response(JSON.stringify([])))
      .mockResolvedValueOnce(new Response(JSON.stringify(runbook)))
    vi.stubGlobal('fetch', fetchMock)
    const signal = new AbortController().signal

    await getDashboardOperations({ limit: 5, activeOnly: true, signal })
    await getDashboardApprovals({ limit: 3, signal })
    await getDashboardInterventions({ limit: 3, signal })
    await expect(getInterventionRunbook('scheduled_action:4', signal)).resolves.toEqual(
      runbook,
    )

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/api/operations?limit=5&active_only=true',
      'http://localhost:8000/api/approvals?limit=3',
      'http://localhost:8000/api/interventions?limit=3',
      'http://localhost:8000/api/interventions/scheduled_action%3A4/runbook',
    ])
    expect(fetchMock.mock.calls.every(([, options]) => options?.signal === signal)).toBe(true)
  })

  it('envía los métodos y cuerpos de las mutaciones', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockImplementation(() =>
        Promise.resolve(new Response(JSON.stringify({ success: true }))),
      )
    vi.stubGlobal('fetch', fetchMock)

    await pauseScheduledAction({ scheduledActionId: 1, reason: 'maintenance' })
    await resumeScheduledAction({ scheduledActionId: 2 })
    await approveScheduledAction({ scheduledActionId: 3, note: 'reviewed' })
    await rejectScheduledAction({ scheduledActionId: 4, note: 'unsafe' })
    await retryIntervention({ interventionId: 'call_flow:5' })

    expect(fetchMock.mock.calls.map(([url, options]) => [url, options?.method, options?.body])).toEqual([
      ['http://localhost:8000/api/scheduled-actions/1/pause', 'POST', '{"reason":"maintenance"}'],
      ['http://localhost:8000/api/scheduled-actions/2/resume', 'POST', undefined],
      ['http://localhost:8000/api/scheduled-actions/3/approve', 'POST', '{"note":"reviewed"}'],
      ['http://localhost:8000/api/scheduled-actions/4/reject', 'POST', '{"note":"unsafe"}'],
      ['http://localhost:8000/api/interventions/call_flow%3A5/retry', 'POST', undefined],
    ])
  })

  it('conserva ApiError y el cuerpo controlado para retry 409', async () => {
    const body = { detail: 'retry_blocked' }
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(JSON.stringify(body), {
          status: 409,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(retryIntervention({ interventionId: 'processed_event:9' })).rejects.toMatchObject({
      status: 409,
      responseBody: body,
    })
  })
})
