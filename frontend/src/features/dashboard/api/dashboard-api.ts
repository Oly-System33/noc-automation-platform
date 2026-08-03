import {
  ApiError,
  getJson,
} from '@/lib/api-client'

import type {
  DashboardIncidentListResponse,
  DashboardSummaryResponse,
  HealthResponse,
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
