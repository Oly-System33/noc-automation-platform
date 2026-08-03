import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { env } from '@/config/env'

import {
  getDashboardApprovals,
  getDashboardInterventions,
  getDashboardOperations,
  getDashboardSummary,
  getHealth,
  getInterventionRunbook,
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

export function useDashboardOperationsQuery(limit = 5, activeOnly = true) {
  return useQuery({
    queryKey: dashboardQueryKeys.operations(limit, activeOnly),
    queryFn: ({ signal }) =>
      getDashboardOperations({ limit, activeOnly, signal }),
    ...pollingOptions,
  })
}

export function useDashboardApprovalsQuery(limit = 3) {
  return useQuery({
    queryKey: dashboardQueryKeys.approvals(limit),
    queryFn: ({ signal }) => getDashboardApprovals({ limit, signal }),
    ...pollingOptions,
  })
}

export function useDashboardInterventionsQuery(limit = 3) {
  return useQuery({
    queryKey: dashboardQueryKeys.interventions(limit),
    queryFn: ({ signal }) => getDashboardInterventions({ limit, signal }),
    ...pollingOptions,
  })
}

export function useInterventionRunbookQuery(
  interventionId: string,
  enabled: boolean,
) {
  return useQuery({
    queryKey: dashboardQueryKeys.runbook(interventionId),
    queryFn: ({ signal }) => getInterventionRunbook(interventionId, signal),
    enabled,
  })
}
