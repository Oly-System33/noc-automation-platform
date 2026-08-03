import {
  ApiError,
  getJson,
  postJson,
} from '@/lib/api-client'

import type {
  ApproveScheduledActionResponse,
  DashboardApprovalListResponse,
  DashboardIncidentListResponse,
  DashboardInterventionListResponse,
  DashboardOperationListResponse,
  DashboardSummaryResponse,
  HealthResponse,
  IncidentDetailResponse,
  AuditLogListResponse,
  OperationalConfigurationResponse,
  InterventionRunbookResponse,
  PauseScheduledActionResponse,
  RejectScheduledActionResponse,
  ResumeScheduledActionResponse,
  RetryInterventionResponse,
} from './dashboard-api.types'
import type {
  ApprovalFilters,
  AuditFilters,
  IncidentFilters,
  InterventionFilters,
  OperationFilters,
} from './dashboard-query-keys'

function value(value?: string) {
  const trimmed = value?.trim()
  return trimmed || undefined
}

function isUnavailableHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const response = value as Record<string, unknown>
  return response.status === 'error' && response.database === 'unavailable'
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  try {
    return await getJson<HealthResponse>('/health', { signal })
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 503 &&
      isUnavailableHealthResponse(error.responseBody)
    ) {
      return error.responseBody
    }

    throw error
  }
}

export function getDashboardSummary(signal?: AbortSignal) {
  return getJson<DashboardSummaryResponse>('/api/dashboard/summary', { signal })
}

type RecentIncidentsOptions = {
  limit: number
  signal?: AbortSignal
}

export function getRecentIncidents({ limit, signal }: RecentIncidentsOptions) {
  return getJson<DashboardIncidentListResponse>('/api/incidents', {
    signal,
    query: { limit },
  })
}

export function getIncidents(filters: IncidentFilters, signal?: AbortSignal) {
  return getJson<DashboardIncidentListResponse>('/api/incidents', {
    signal,
    query: {
      limit: filters.limit, offset: filters.offset, search: value(filters.search),
      client: value(filters.client), severity: value(filters.severity),
      status: value(filters.status), incident_status: value(filters.incidentStatus),
    },
  })
}

export function getIncidentDetail(eventId: string, signal?: AbortSignal) {
  return getJson<IncidentDetailResponse>(`/api/incidents/${encodeURIComponent(eventId)}`, { signal })
}

type ListOptions = {
  limit: number
  signal?: AbortSignal
}

type OperationListOptions = ListOptions & {
  activeOnly: boolean
}

export function getDashboardOperations({
  limit,
  activeOnly,
  signal,
}: OperationListOptions) {
  return getJson<DashboardOperationListResponse>('/api/operations', {
    signal,
    query: { limit, active_only: activeOnly },
  })
}

export function getDashboardApprovals({ limit, signal }: ListOptions) {
  return getJson<DashboardApprovalListResponse>('/api/approvals', {
    signal,
    query: { limit },
  })
}

export function getDashboardInterventions({ limit, signal }: ListOptions) {
  return getJson<DashboardInterventionListResponse>('/api/interventions', {
    signal,
    query: { limit },
  })
}

export function getOperations(filters: OperationFilters, signal?: AbortSignal) {
  return getJson<DashboardOperationListResponse>('/api/operations', { signal, query: {
    limit: filters.limit, offset: filters.offset, search: value(filters.search),
    client: value(filters.client), status: value(filters.status), action: value(filters.action),
    internal_state: value(filters.internalState), active_only: filters.activeOnly,
  } })
}

export function getApprovals(filters: ApprovalFilters, signal?: AbortSignal) {
  return getJson<DashboardApprovalListResponse>('/api/approvals', { signal, query: {
    status: filters.status, limit: filters.limit, offset: filters.offset,
    search: value(filters.search), client: value(filters.client),
  } })
}

export function getInterventions(filters: InterventionFilters, signal?: AbortSignal) {
  return getJson<DashboardInterventionListResponse>('/api/interventions', { signal, query: {
    limit: filters.limit, offset: filters.offset, search: value(filters.search),
    source_type: value(filters.sourceType), status: value(filters.status),
  } })
}

export function getAuditLogs(filters: AuditFilters, signal?: AbortSignal) {
  return getJson<AuditLogListResponse>('/api/audit-logs', { signal, query: {
    limit: filters.limit, offset: filters.offset, search: value(filters.search),
    level: value(filters.level), component: value(filters.component), event_id: value(filters.eventId),
    created_from: value(filters.createdFrom), created_to: value(filters.createdTo),
  } })
}

export function getOperationalConfiguration(signal?: AbortSignal) {
  return getJson<OperationalConfigurationResponse>('/api/configuration/operational', { signal })
}

export function getInterventionRunbook(
  interventionId: string,
  signal?: AbortSignal,
) {
  return getJson<InterventionRunbookResponse>(
    `/api/interventions/${encodeURIComponent(interventionId)}/runbook`,
    { signal },
  )
}

type ScheduledActionMutationOptions = {
  scheduledActionId: number
  signal?: AbortSignal
}

export function pauseScheduledAction({
  scheduledActionId,
  reason,
  signal,
}: ScheduledActionMutationOptions & { reason?: string | null }) {
  return postJson<PauseScheduledActionResponse>(
    `/api/scheduled-actions/${scheduledActionId}/pause`,
    { body: reason === undefined ? undefined : { reason }, signal },
  )
}

export function resumeScheduledAction({
  scheduledActionId,
  signal,
}: ScheduledActionMutationOptions) {
  return postJson<ResumeScheduledActionResponse>(
    `/api/scheduled-actions/${scheduledActionId}/resume`,
    { signal },
  )
}

export function approveScheduledAction({
  scheduledActionId,
  note,
  signal,
}: ScheduledActionMutationOptions & { note?: string | null }) {
  return postJson<ApproveScheduledActionResponse>(
    `/api/scheduled-actions/${scheduledActionId}/approve`,
    { body: note === undefined ? undefined : { note }, signal },
  )
}

export function rejectScheduledAction({
  scheduledActionId,
  note,
  signal,
}: ScheduledActionMutationOptions & { note?: string | null }) {
  return postJson<RejectScheduledActionResponse>(
    `/api/scheduled-actions/${scheduledActionId}/reject`,
    { body: note === undefined ? undefined : { note }, signal },
  )
}

export function retryIntervention({
  interventionId,
  signal,
}: {
  interventionId: string
  signal?: AbortSignal
}) {
  return postJson<RetryInterventionResponse>(
    `/api/interventions/${encodeURIComponent(interventionId)}/retry`,
    { signal },
  )
}
