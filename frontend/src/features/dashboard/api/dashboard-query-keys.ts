export type IncidentFilters = Readonly<{
  limit: number
  offset: number
  search?: string
  client?: string
  severity?: string
  status?: string
  incidentStatus?: string
}>

export type OperationFilters = Readonly<{
  limit: number
  offset: number
  search?: string
  client?: string
  status?: string
  action?: string
  internalState?: string
  activeOnly?: boolean
}>

export type ApprovalFilters = Readonly<{
  limit: number
  offset: number
  status: 'pending' | 'approved' | 'rejected' | 'all'
  search?: string
  client?: string
}>

export type InterventionFilters = Readonly<{
  limit: number
  offset: number
  search?: string
  sourceType?: string
  status?: string
}>

export type AuditFilters = Readonly<{
  limit: number
  offset: number
  search?: string
  level?: string
  component?: string
  eventId?: string
  createdFrom?: string
  createdTo?: string
}>

function normalized<T extends object>(filters: T): Readonly<T> {
  return Object.freeze({ ...filters })
}

export const dashboardQueryKeys = {
  all: ['dashboard'] as const,
  health: () => [...dashboardQueryKeys.all, 'health'] as const,
  summary: () => [...dashboardQueryKeys.all, 'summary'] as const,
  incidentLists: () => [...dashboardQueryKeys.all, 'incidents'] as const,
  incidents: (limit: number) =>
    [...dashboardQueryKeys.incidentLists(), { limit }] as const,
  incidentList: (filters: IncidentFilters) =>
    [...dashboardQueryKeys.incidentLists(), normalized(filters)] as const,
  incidentDetails: () => [...dashboardQueryKeys.all, 'incident-detail'] as const,
  incidentDetail: (eventId: string) =>
    [...dashboardQueryKeys.incidentDetails(), eventId] as const,
  operationLists: () => [...dashboardQueryKeys.all, 'operations'] as const,
  operations: (limit: number, activeOnly: boolean) =>
    [...dashboardQueryKeys.operationLists(), { limit, activeOnly }] as const,
  operationList: (filters: OperationFilters) =>
    [...dashboardQueryKeys.operationLists(), normalized(filters)] as const,
  approvalLists: () => [...dashboardQueryKeys.all, 'approvals'] as const,
  approvals: (limit: number) =>
    [...dashboardQueryKeys.approvalLists(), { limit }] as const,
  approvalList: (filters: ApprovalFilters) =>
    [...dashboardQueryKeys.approvalLists(), normalized(filters)] as const,
  interventionLists: () => [...dashboardQueryKeys.all, 'interventions'] as const,
  interventions: (limit: number) =>
    [...dashboardQueryKeys.interventionLists(), { limit }] as const,
  interventionList: (filters: InterventionFilters) =>
    [...dashboardQueryKeys.interventionLists(), normalized(filters)] as const,
  auditLists: () => [...dashboardQueryKeys.all, 'audit-logs'] as const,
  auditList: (filters: AuditFilters) =>
    [...dashboardQueryKeys.auditLists(), normalized(filters)] as const,
  configuration: () => [...dashboardQueryKeys.all, 'configuration'] as const,
  runbook: (interventionId: string) =>
    [...dashboardQueryKeys.all, 'runbooks', interventionId] as const,
}
