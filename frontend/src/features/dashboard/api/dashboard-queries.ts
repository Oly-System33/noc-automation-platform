import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { env } from '@/config/env'

import {
  getDashboardSummary,
  getHealth,
  getRecentIncidents,
} from './dashboard-api'
import { dashboardQueryKeys } from './dashboard-query-keys'

const pollingOptions = {
  refetchInterval: env.pollIntervalMs,
  placeholderData: keepPreviousData,
} as const

export function useHealthQuery() {
  return useQuery({
    queryKey: dashboardQueryKeys.health(),
    queryFn: ({ signal }) => getHealth(signal),
    ...pollingOptions,
  })
}

export function useDashboardSummaryQuery() {
  return useQuery({
    queryKey: dashboardQueryKeys.summary(),
    queryFn: ({ signal }) => getDashboardSummary(signal),
    ...pollingOptions,
  })
}

export function useRecentIncidentsQuery(limit = 6) {
  return useQuery({
    queryKey: dashboardQueryKeys.incidents(limit),
    queryFn: ({ signal }) => getRecentIncidents({ limit, signal }),
    ...pollingOptions,
  })
}
