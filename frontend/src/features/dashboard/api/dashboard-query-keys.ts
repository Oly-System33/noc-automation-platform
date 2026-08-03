export const dashboardQueryKeys = {
  all: ['dashboard'] as const,
  health: () => [...dashboardQueryKeys.all, 'health'] as const,
  summary: () => [...dashboardQueryKeys.all, 'summary'] as const,
  incidentLists: () => [...dashboardQueryKeys.all, 'incidents'] as const,
  incidents: (limit: number) =>
    [...dashboardQueryKeys.incidentLists(), { limit }] as const,
  operationLists: () => [...dashboardQueryKeys.all, 'operations'] as const,
  operations: (limit: number, activeOnly: boolean) =>
    [...dashboardQueryKeys.operationLists(), { limit, activeOnly }] as const,
  approvalLists: () => [...dashboardQueryKeys.all, 'approvals'] as const,
  approvals: (limit: number) =>
    [...dashboardQueryKeys.approvalLists(), { limit }] as const,
  interventionLists: () => [...dashboardQueryKeys.all, 'interventions'] as const,
  interventions: (limit: number) =>
    [...dashboardQueryKeys.interventionLists(), { limit }] as const,
  runbook: (interventionId: string) =>
    [...dashboardQueryKeys.all, 'runbooks', interventionId] as const,
}
