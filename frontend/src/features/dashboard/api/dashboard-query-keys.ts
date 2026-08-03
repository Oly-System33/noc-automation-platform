export const dashboardQueryKeys = {
  all: ['dashboard'] as const,
  health: () => [...dashboardQueryKeys.all, 'health'] as const,
  summary: () => [...dashboardQueryKeys.all, 'summary'] as const,
  incidents: (limit: number) =>
    [...dashboardQueryKeys.all, 'incidents', { limit }] as const,
}
