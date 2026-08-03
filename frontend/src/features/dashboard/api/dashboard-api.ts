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
  InterventionRunbookResponse,
  PauseScheduledActionResponse,
  RejectScheduledActionResponse,
  ResumeScheduledActionResponse,
  RetryInterventionResponse,
} from './dashboard-api.types'

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
