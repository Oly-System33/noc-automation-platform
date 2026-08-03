import { ApprovalsTable } from '@/features/dashboard/components/approvals-table'
import { DashboardHeader } from '@/features/dashboard/components/dashboard-header'
import { DashboardSidebar } from '@/features/dashboard/components/dashboard-sidebar'
import { IncidentsTable } from '@/features/dashboard/components/incidents-table'
import { KpiGrid } from '@/features/dashboard/components/kpi-grid'
import { ManualInterventionTable } from '@/features/dashboard/components/manual-intervention-table'
import { OperationsTable } from '@/features/dashboard/components/operations-table'
import { useCompactElapsedTime } from '@/features/dashboard/hooks/use-compact-elapsed-time'
import { mapIncidentListToUi } from '@/features/dashboard/mappers/dashboard-data.mapper'
import { mapHealthQueryState } from '@/features/dashboard/mappers/dashboard-health.mapper'
import { formatPollingInterval } from '@/features/dashboard/mappers/dashboard-time.mapper'

export function DashboardPage() {
  const healthQuery = useHealthQuery()
  const summaryQuery = useDashboardSummaryQuery()
  const incidentsQuery = useRecentIncidentsQuery(6)
  const health = mapHealthQueryState(healthQuery)
  const incidents = mapIncidentListToUi(incidentsQuery.data)
  const lastUpdatedAt = Math.max(
    summaryQuery.dataUpdatedAt,
    incidentsQuery.dataUpdatedAt,
  )
  const lastUpdatedLabel = useCompactElapsedTime(lastUpdatedAt)
  const isRefreshing =
    healthQuery.isFetching ||
    summaryQuery.isFetching ||
    incidentsQuery.isFetching

  function refreshDashboard() {
    void Promise.all([
      healthQuery.refetch(),
      summaryQuery.refetch(),
      incidentsQuery.refetch(),
    ])
  }

  return (
    <div className="flex h-svh min-w-[1180px] overflow-hidden bg-background">
      <DashboardSidebar
        apiState={health.api}
        databaseState={health.database}
      />
      <main className="noc-scrollbar min-w-0 flex-1 overflow-y-auto p-2">
        <div className="flex min-h-full flex-col gap-2">
          <DashboardHeader
            apiState={health.api}
            databaseState={health.database}
            pollingLabel={formatPollingInterval(env.pollIntervalMs)}
            lastUpdatedLabel={lastUpdatedLabel}
            isRefreshing={isRefreshing}
            onRefresh={refreshDashboard}
          />
          <KpiGrid
            counts={summaryQuery.data?.counts}
            isLoading={summaryQuery.isPending}
            isError={summaryQuery.isError}
            isRetrying={summaryQuery.isFetching}
            onRetry={() => void summaryQuery.refetch()}
          />
          <IncidentsTable
            incidents={incidents}
            hasResponse={incidentsQuery.data !== undefined}
            isLoading={incidentsQuery.isPending}
            isError={incidentsQuery.isError}
            isFetching={incidentsQuery.isFetching}
            onRetry={() => void incidentsQuery.refetch()}
          />
          <div className="grid grid-cols-1 gap-2 min-[1180px]:grid-cols-[0.86fr_1.04fr]">
            <OperationsTable />
            <ApprovalsTable />
          </div>
          <ManualInterventionTable />
        </div>
      </main>
    </div>
  )
}
import { env } from '@/config/env'
import {
  useDashboardSummaryQuery,
  useHealthQuery,
  useRecentIncidentsQuery,
} from '@/features/dashboard/api/dashboard-queries'
