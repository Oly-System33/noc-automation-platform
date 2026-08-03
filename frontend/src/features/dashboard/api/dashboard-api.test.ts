import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api-client'

import {
  getDashboardSummary,
  getHealth,
  getRecentIncidents,
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
})
