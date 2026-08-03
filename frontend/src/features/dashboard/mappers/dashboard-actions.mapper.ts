import type {
  DashboardInterventionListResponse,
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

export function mapOperationsToUi(
  response?: DashboardOperationListResponse,
): Operation[] {
  if (!response) return []

  return response.items.map((item, index) => ({
    rowId: `${item.scheduled_action_id}:${item.action ?? 'unknown'}:${index}`,
    scheduledActionId: item.scheduled_action_id,
    action: item.action,
    client: item.client?.trim() || DASH,
    status: mapDashboardStatusToLabel(item.display_status),
    target: item.target?.trim() || DASH,
    attempts: item.attempt_count === null ? DASH : String(item.attempt_count),
    control:
      item.internal_state === 'pending'
        ? 'Pausar'
        : item.internal_state === 'paused'
          ? 'Reanudar'
          : null,
  }))
}

export function mapApprovalsToUi(
  response?: DashboardOperationListResponse,
): Approval[] {
  if (!response) return []

  return response.items.map((item) => ({
    scheduledActionId: item.scheduled_action_id,
    id: String(item.scheduled_action_id),
    client: item.client?.trim() || DASH,
    objective: [item.action?.trim(), item.target?.trim()]
      .filter(Boolean)
      .join(' / ') || DASH,
    reason: item.trigger?.trim() || DASH,
    time: formatCompactAge(
      item.created_at ?? item.scheduled_at,
      response.generated_at,
    ),
  }))
}

export function mapInterventionsToUi(
  response?: DashboardInterventionListResponse,
): ManualIntervention[] {
  if (!response) return []

  return response.map((item) => ({
    interventionId: item.intervention_id,
    eventId: item.event_id ?? DASH,
    client: item.client?.trim() || DASH,
    host: item.host?.trim() || DASH,
    description: item.description?.trim() || item.failure_reason || DASH,
    severity: mapSeverityToLabel(item.severity),
    status: mapDashboardStatusToLabel(item.status),
    time: formatCompactAge(item.detected_at),
    failureReason: item.failure_reason,
    retrySupported: item.retry_supported,
    runbookAvailable: item.runbook_available,
  }))
}
