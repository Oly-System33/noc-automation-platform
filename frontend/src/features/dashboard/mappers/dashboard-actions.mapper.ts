import type {
  DashboardInterventionListResponse,
  DashboardApprovalListResponse,
  DashboardOperationListResponse,
} from '@/features/dashboard/api/dashboard-api.types'
import { mapSeverityToLabel } from '@/features/dashboard/mappers/dashboard-severity.mapper'
import { mapDashboardStatusToLabel } from '@/features/dashboard/mappers/dashboard-status.mapper'
import { formatCompactAge } from '@/features/dashboard/mappers/dashboard-time.mapper'
import type {
  Approval,
  ManualIntervention,
  Operation,
} from '@/features/dashboard/types/dashboard-ui'

const DASH = '—'

function formatTimestamp(value: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : DASH
}

export function mapOperationsToUi(
  response?: DashboardOperationListResponse,
): Operation[] {
  if (!response) return []

  return response.items.map((item, index) => ({
    rowId: `${item.scheduled_action_id}:${item.action ?? 'unknown'}:${index}`,
    scheduledActionId: item.scheduled_action_id,
    eventId: item.event_id,
    action: item.action,
    client: item.client?.trim() || DASH,
    status: mapDashboardStatusToLabel(item.display_status),
    target: item.target?.trim() || DASH,
    attempts: item.attempt_count === null ? DASH : String(item.attempt_count),
    attemptCount: item.attempt_count === null ? DASH : String(item.attempt_count),
    maxAttempts: item.max_attempts === null ? DASH : String(item.max_attempts),
    createdAt: formatTimestamp(item.created_at),
    activityAt: formatTimestamp(item.activity_at),
    control:
      item.internal_state === 'pending'
        ? 'Pausar'
        : item.internal_state === 'paused'
          ? 'Reanudar'
          : null,
  }))
}

export function mapApprovalsToUi(
  response?: DashboardApprovalListResponse,
): Approval[] {
  if (!response) return []

  return response.items.map((item) => ({
    scheduledActionId: item.scheduled_action_id,
    eventId: item.event_id,
    id: String(item.scheduled_action_id),
    client: item.client?.trim() || DASH,
    objective: [item.action?.trim(), item.target?.trim()]
      .filter(Boolean)
      .join(' / ') || DASH,
    reason: item.reason?.trim() || DASH,
    time: formatCompactAge(
      item.requested_at,
      response.generated_at,
    ),
    decision: item.decision ?? 'unknown',
    result: item.result,
    operationState: item.operation_state,
    requestedAt: formatTimestamp(item.requested_at),
    decidedAt: formatTimestamp(item.decided_at),
  }))
}

export function mapInterventionsToUi(
  response?: DashboardInterventionListResponse,
): ManualIntervention[] {
  if (!response) return []

  return response.items.map((item) => ({
    interventionId: item.intervention_id,
    sourceType: item.source_type,
    eventId: item.event_id ?? DASH,
    client: item.client?.trim() || DASH,
    host: item.host?.trim() || DASH,
    description: item.description?.trim() || item.failure_reason || DASH,
    severity: mapSeverityToLabel(item.severity),
    status: mapDashboardStatusToLabel(item.status),
    time: formatCompactAge(item.detected_at, response.generated_at),
    failureReason: item.failure_reason,
    attempts: item.attempt_count === null
      ? DASH
      : `${item.attempt_count}/${item.max_attempts ?? DASH}`,
    retrySupported: item.retry_supported,
    retryBlockedReason: item.retry_blocked_reason,
    runbookAvailable: item.runbook_available,
  }))
}
