import { vi } from 'vitest'

import type {
  DashboardIncident,
  DashboardIncidentListResponse,
  DashboardSummaryResponse,
  HealthResponse,
} from '@/features/dashboard/api/dashboard-api.types'

export const healthResponse: HealthResponse = {
  status: 'ok',
  database: 'ok',
}

export const summaryResponse: DashboardSummaryResponse = {
  generated_at: '2026-08-03T12:00:00Z',
  counts: {
    active: 12,
    scheduled: 6,
    paused: 3,
    pending_approval: 2,
    executing: 4,
    waiting_confirmation: 5,
    retry_scheduled: 7,
    manual_required: 8,
    stuck: 1,
    failed: 2,
    cancelled: 9,
    closed: 28,
  },
  by_client: { 'Banco X': 6 },
  total: 87,
}

function createIncident(
  eventId: string,
  overrides: Partial<DashboardIncident>,
): DashboardIncident {
  return {
    event_id: eventId,
    display_status: 'active',
    client: null,
    host: null,
    trigger: null,
    severity: null,
    incident_status: null,
    opened_at: null,
    updated_at: null,
    current_action: null,
    target: null,
    scheduled_action_id: null,
    scheduled_action_state: null,
    scheduled_at: null,
    paused_at: null,
    resumed_at: null,
    attempt_count: null,
    call_flow_state: null,
    stuck_since: null,
    error_message: null,
    ...overrides,
  }
}

export const incidentsResponse: DashboardIncidentListResponse = {
  generated_at: '2026-08-03T12:00:00Z',
  total: 6,
  items: [
    createIncident('event-0512', {
      client: 'Banco X',
      host: 'srv-core-01',
      trigger: 'Zabbix agent unreachable',
      severity: 'Critical',
      display_status: 'active',
      current_action: 'jira',
      opened_at: '2026-08-03T11:58:00Z',
    }),
    createIncident('event-0511', {
      client: 'Banco Demo',
      host: 'db-prod-02',
      trigger: 'High CPU',
      severity: 'High',
      display_status: 'executing',
      current_action: 'calls',
      opened_at: '2026-08-03T11:56:00Z',
    }),
    createIncident('event-0510', {
      client: 'Banco X',
      host: 'app-web-03',
      trigger: 'Disk space low',
      severity: 'Warning',
      display_status: 'scheduled',
      current_action: 'telegram',
      opened_at: '2026-08-03T11:48:00Z',
    }),
    createIncident('event-0509', {
      client: 'Banco Demo',
      host: 'net-fw-01',
      trigger: 'Interface down',
      severity: 'Average',
      display_status: 'paused',
      current_action: 'email',
      opened_at: '2026-08-03T11:42:00Z',
    }),
    createIncident('event-0508', {
      client: 'Banco X',
      host: 'db-replica-01',
      trigger: 'Replication lag high',
      severity: 'High',
      display_status: 'pending_approval',
      current_action: 'jira, telegram',
      opened_at: '2026-08-03T11:33:00Z',
    }),
    createIncident('event-0507', {
      client: 'Banco Demo',
      host: 'vm-app-07',
      trigger: 'Service not responding',
      severity: 'Information',
      display_status: 'stuck',
      current_action: null,
      opened_at: '2026-08-03T11:23:00Z',
    }),
  ],
}

type DashboardFetchOptions = {
  health?: HealthResponse
  summary?: DashboardSummaryResponse
  incidents?: DashboardIncidentListResponse
  failingPaths?: string[]
}

export function installDashboardFetchMock({
  health = healthResponse,
  summary = summaryResponse,
  incidents = incidentsResponse,
  failingPaths = [],
}: DashboardFetchOptions = {}) {
  const fetchMock = vi.fn(async (input: string | URL | Request) => {
    const requestUrl =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url
    const url = new URL(requestUrl)

    if (failingPaths.includes(url.pathname)) {
      return new Response(JSON.stringify({ detail: 'internal-sensitive-data' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    if (url.pathname === '/health') {
      return new Response(JSON.stringify(health), {
        status: health.status === 'ok' ? 200 : 503,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    if (url.pathname === '/api/dashboard/summary') {
      return Response.json(summary)
    }

    if (url.pathname === '/api/incidents') {
      return Response.json(incidents)
    }

    throw new Error(`Unexpected test request: ${url.pathname}`)
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
