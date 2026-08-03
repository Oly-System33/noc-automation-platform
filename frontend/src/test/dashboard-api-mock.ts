import { vi } from 'vitest'

import type {
  DashboardIncident,
  DashboardIncidentListResponse,
  DashboardInterventionListResponse,
  DashboardOperationListResponse,
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

const operationBase = {
  event_id: 'event-operation', client: 'Banco X', host: 'host-1', trigger: 'High CPU', severity: 'High', incident_status: 'open', target: 'NOC', processing_started_at: null, paused_at: null, resumed_at: null, attempt_count: 1, created_at: '2026-08-03T11:50:00Z', pause_reason: null, cancel_reason: null, error_message: null,
} as const

export const operationsResponse: DashboardOperationListResponse = {
  generated_at: '2026-08-03T12:00:00Z', total: 2,
  items: [
    { ...operationBase, scheduled_action_id: 41, action: 'jira', internal_state: 'pending', display_status: 'scheduled', scheduled_at: '2026-08-03T12:10:00Z' },
    { ...operationBase, scheduled_action_id: 42, action: 'email', internal_state: 'paused', display_status: 'paused', scheduled_at: '2026-08-03T11:55:00Z' },
  ],
}

export const approvalsResponse: DashboardOperationListResponse = {
  generated_at: '2026-08-03T12:00:00Z', total: 1,
  items: [{ ...operationBase, scheduled_action_id: 51, action: 'script', internal_state: 'pending_approval', display_status: 'pending_approval', scheduled_at: '2026-08-03T12:05:00Z' }],
}

export const interventionsResponse: DashboardInterventionListResponse = [
  { intervention_id: 'call_flow:61', source_type: 'call_flow', source_id: 61, event_id: 'event-manual', client: 'Banco Demo', host: 'voice-01', description: 'Confirmación manual requerida', severity: 'Critical', status: 'manual_required', detected_at: '2026-08-03T11:45:00Z', attempt_count: 3, max_attempts: 3, failure_reason: 'Intervención operativa requerida', retry_supported: false, retry_blocked_reason: 'retry_not_safe', runbook_available: true },
]

type DashboardFetchOptions = {
  health?: HealthResponse
  summary?: DashboardSummaryResponse
  incidents?: DashboardIncidentListResponse
  operations?: DashboardOperationListResponse
  approvals?: DashboardOperationListResponse
  interventions?: DashboardInterventionListResponse
  failingPaths?: string[]
}

export function installDashboardFetchMock({
  health = healthResponse,
  summary = summaryResponse,
  incidents = incidentsResponse,
  operations = operationsResponse,
  approvals = approvalsResponse,
  interventions = interventionsResponse,
  failingPaths = [],
}: DashboardFetchOptions = {}) {
  const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const requestUrl =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url
    const url = new URL(requestUrl)
    const method = init?.method ?? 'GET'

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

    if (url.pathname === '/api/operations') return Response.json(operations)
    if (url.pathname === '/api/approvals') return Response.json(approvals)
    if (url.pathname === '/api/interventions' && method === 'GET') return Response.json(interventions)
    if (url.pathname.endsWith('/runbook') && method === 'GET') return Response.json({ intervention_id: 'call_flow:61', source: 'current_runbook', warning: 'Runbook actual', actions: ['calls'], target: 'NOC', delay_minutes: 0, execution_mode: 'immediate', approval_when: 'never', pre_actions: [], pre_target: null })
    if (url.pathname.includes('/api/scheduled-actions/') && method === 'POST') {
      const id = Number(url.pathname.split('/')[3])
      if (url.pathname.endsWith('/pause')) return Response.json({ success: true, scheduled_action_id: id, state: 'paused' })
      if (url.pathname.endsWith('/resume')) return Response.json({ success: true, scheduled_action_id: id, state: 'processing', execution_started: true }, { status: 202 })
      if (url.pathname.endsWith('/approve')) return Response.json({ success: true, scheduled_action_id: id, previous_state: 'pending_approval', state: 'processing', approved: true, execution_started: true }, { status: 202 })
      if (url.pathname.endsWith('/reject')) return Response.json({ success: true, scheduled_action_id: id, previous_state: 'pending_approval', state: 'cancelled', rejected: true })
    }
    if (url.pathname.endsWith('/retry') && method === 'POST') return Response.json({ detail: 'retry_not_safe', code: 'retry_not_safe' }, { status: 409 })

    throw new Error(`Unexpected test request: ${url.pathname}`)
  })

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
