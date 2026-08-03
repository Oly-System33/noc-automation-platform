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

export type DashboardOperationItem = {
  scheduled_action_id: number
  event_id: string
  client: string | null
  host: string | null
  trigger: string | null
  severity: string | null
  incident_status: string | null
  action: string | null
  target: string | null
  internal_state: string
  display_status: DashboardOperationStatus
  scheduled_at: string | null
  processing_started_at: string | null
  paused_at: string | null
  resumed_at: string | null
  attempt_count: number | null
  created_at: string | null
  pause_reason: string | null
  cancel_reason: string | null
  error_message: string | null
}

export type DashboardOperationStatus =
  | 'scheduled'
  | 'pending_approval'
  | 'paused'
  | 'executing'
  | 'stuck'
  | 'executed'
  | 'failed'
  | 'cancelled'

export type DashboardOperationListResponse = {
  items: DashboardOperationItem[]
  total: number
  generated_at: string
}

export type DashboardApprovalListResponse = DashboardOperationListResponse

export type InterventionSourceType =
  | 'scheduled_action'
  | 'processed_event'
  | 'call_flow'

export type InterventionStatus = 'manual_required' | 'stuck' | 'failed'

export type DashboardInterventionItem = {
  intervention_id: string
  source_type: InterventionSourceType
  source_id: number
  event_id: string | null
  client: string | null
  host: string | null
  description: string | null
  severity: string | null
  status: InterventionStatus
  detected_at: string
  attempt_count: number | null
  max_attempts: number | null
  failure_reason: string
  retry_supported: false
  retry_blocked_reason: 'retry_not_safe'
  runbook_available: boolean
}

export type DashboardInterventionListResponse = DashboardInterventionItem[]

export type InterventionRunbookResponse = {
  intervention_id: string
  source: 'persisted_action_plan' | 'current_runbook'
  warning: string | null
  actions: string[]
  target: string | null
  delay_minutes: number | null
  execution_mode: string | null
  approval_when: string | null
  pre_actions: string[]
  pre_target: string | null
}

export type PauseScheduledActionResponse = {
  success: boolean
  scheduled_action_id: number
  state: string
}

export type ResumeScheduledActionResponse = PauseScheduledActionResponse & {
  execution_started: boolean
}

export type ApproveScheduledActionResponse = ResumeScheduledActionResponse & {
  previous_state: string
  approved: boolean
}

export type RejectScheduledActionResponse = PauseScheduledActionResponse & {
  previous_state: string
  rejected: boolean
}

export type RetryInterventionResponse = {
  success: boolean
  intervention_id: string
  state?: string
  retry_started?: boolean
}
