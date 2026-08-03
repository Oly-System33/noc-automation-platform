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
  closed_at: string | null
  duration: string | null
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
  limit: number
  offset: number
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
  activity_at: string | null
  executed_at: string | null
  cancelled_at: string | null
  max_attempts: number | null
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
  limit: number
  offset: number
  generated_at: string
}

export type DashboardApprovalItem = {
  scheduled_action_id: number
  event_id: string
  client: string | null
  action: string | null
  target: string | null
  reason: string | null
  decision: 'pending' | 'approved' | 'rejected' | null
  requested_at: string | null
  decided_at: string | null
  operation_state: string
  result: string | null
  display_status: DashboardOperationStatus
  created_at: string | null
}

export type DashboardApprovalListResponse = ListEnvelope<DashboardApprovalItem>

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
  retry_supported: boolean
  retry_blocked_reason: string | null
  runbook_available: boolean
}

export type ListEnvelope<T> = {
  items: T[]
  total: number
  limit: number
  offset: number
  generated_at: string
}

export type DashboardInterventionListResponse = ListEnvelope<DashboardInterventionItem>

export type IncidentDetailRecord = {
  id?: number | string | null
  action_id?: number | null
  call_attempt_id?: number | null
  audit_log_id?: number | null
  scheduled_action_id?: number | null
  event_id?: string | null
  state?: string | null
  status?: string | null
  display_status?: string | null
  action?: string | null
  operation?: string | null
  result?: string | null
  message?: string | null
  failure_reason?: string | null
  reason?: string | null
  decision?: string | null
  operation_state?: string | null
  level?: string | null
  component?: string | null
  attempt_number?: number | null
  created_at?: string | null
  updated_at?: string | null
  activity_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  attempted_at?: string | null
  decided_at?: string | null
  requested_at?: string | null
  detected_at?: string | null
  source_type?: string | null
}

export type IncidentDetailResponse = DashboardIncident & {
  closed_at: string | null
  duration: string | null
  trigger_group: string | null
  operations: IncidentDetailRecord[]
  actions: IncidentDetailRecord[]
  call_attempts: IncidentDetailRecord[]
  approvals: IncidentDetailRecord[]
  interventions: IncidentDetailRecord[]
  audit_logs: IncidentDetailRecord[]
}

export type AuditLogItem = {
  id: number
  created_at: string
  level: string
  component: string
  event_id: string | null
  scheduled_action_id: number | null
  operation: string | null
  message: string
  context: Record<string, unknown> | null
}

export type AuditLogListResponse = ListEnvelope<AuditLogItem>

export type OperationalConfigurationResponse = {
  generated_at: string
  worker: {
    enabled: boolean
    running: boolean
    ready: boolean
    poll_interval_seconds: number
    batch_size: number
    processing_timeout_minutes: number
    max_attempts: number
  }
  runbooks: {
    available: boolean
    count: number
    cache_count: number
    last_reload: string | null
  }
}

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
