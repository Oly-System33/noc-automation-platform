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
  getApprovals,
  getAuditLogs,
  getIncidentDetail,
  getIncidents,
  getInterventions,
  getOperationalConfiguration,
  getOperations,
} from './dashboard-api'
import { dashboardQueryKeys } from './dashboard-query-keys'
import type { ApprovalFilters, AuditFilters, IncidentFilters, InterventionFilters, OperationFilters } from './dashboard-query-keys'

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

const pageOptions = { placeholderData: keepPreviousData } as const

export function useIncidentsQuery(filters: IncidentFilters) {
  return useQuery({ queryKey: dashboardQueryKeys.incidentList(filters), queryFn: ({ signal }) => getIncidents(filters, signal), ...pageOptions })
}

export function useIncidentDetailQuery(eventId: string) {
  return useQuery({ queryKey: dashboardQueryKeys.incidentDetail(eventId), queryFn: ({ signal }) => getIncidentDetail(eventId, signal), enabled: eventId.length > 0 })
}

export function useOperationsQuery(filters: OperationFilters, enabled = true) {
  return useQuery({ queryKey: dashboardQueryKeys.operationList(filters), queryFn: ({ signal }) => getOperations(filters, signal), enabled, ...pageOptions })
}

export function useApprovalsQuery(filters: ApprovalFilters) {
  return useQuery({ queryKey: dashboardQueryKeys.approvalList(filters), queryFn: ({ signal }) => getApprovals(filters, signal), ...pageOptions })
}

export function useInterventionsQuery(filters: InterventionFilters, enabled = true) {
  return useQuery({ queryKey: dashboardQueryKeys.interventionList(filters), queryFn: ({ signal }) => getInterventions(filters, signal), enabled, ...pageOptions })
}

export function useAuditLogsQuery(filters: AuditFilters) {
  return useQuery({ queryKey: dashboardQueryKeys.auditList(filters), queryFn: ({ signal }) => getAuditLogs(filters, signal), ...pageOptions })
}

export function useOperationalConfigurationQuery() {
  return useQuery({ queryKey: dashboardQueryKeys.configuration(), queryFn: ({ signal }) => getOperationalConfiguration(signal) })
}
