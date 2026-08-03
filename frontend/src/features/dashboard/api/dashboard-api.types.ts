export type HealthResponse =
  | { status: 'ok'; database: 'ok' }
  | { status: 'error'; database: 'unavailable' }

export type DashboardStatus =
  | 'active'
  | 'scheduled'
  | 'paused'
  | 'pending_approval'
  | 'executing'
  | 'waiting_confirmation'
  | 'retry_scheduled'
  | 'manual_required'
  | 'stuck'
  | 'failed'
  | 'cancelled'
  | 'closed'

export type DashboardStatusCounts = Record<DashboardStatus, number>

export type DashboardSummaryResponse = {
  generated_at: string
  counts: DashboardStatusCounts
  by_client: Record<string, number>
  total: number
}

export type DashboardIncident = {
  event_id: string
  display_status: DashboardStatus
  client: string | null
  host: string | null
  trigger: string | null
  severity: string | null
  incident_status: string | null
  opened_at: string | null
  updated_at: string | null
  current_action: string | null
  target: string | null
  scheduled_action_id: number | null
  scheduled_action_state: string | null
  scheduled_at: string | null
  paused_at: string | null
  resumed_at: string | null
  attempt_count: number | null
  call_flow_state: string | null
  stuck_since: string | null
  error_message: string | null
}

export type DashboardIncidentListResponse = {
  items: DashboardIncident[]
  total: number
  generated_at: string
}
