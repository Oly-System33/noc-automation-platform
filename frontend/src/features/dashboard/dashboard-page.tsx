import { useState } from 'react'

import { env } from '@/config/env'
import {
  useApproveScheduledActionMutation,
  usePauseScheduledActionMutation,
  useRejectScheduledActionMutation,
  useResumeScheduledActionMutation,
  useRetryInterventionMutation,
} from '@/features/dashboard/api/dashboard-mutations'
import {
  useDashboardApprovalsQuery,
  useDashboardInterventionsQuery,
  useDashboardOperationsQuery,
  useDashboardSummaryQuery,
  useHealthQuery,
  useRecentIncidentsQuery,
} from '@/features/dashboard/api/dashboard-queries'
import { ApprovalsTable } from '@/features/dashboard/components/approvals-table'
import { DashboardHeader } from '@/features/dashboard/components/dashboard-header'
import {
  DashboardNotification,
  type DashboardNotice,
} from '@/features/dashboard/components/dashboard-notification'
import { DashboardSidebar } from '@/features/dashboard/components/dashboard-sidebar'
import { IncidentsTable } from '@/features/dashboard/components/incidents-table'
import { KpiGrid } from '@/features/dashboard/components/kpi-grid'
import { ManualInterventionTable } from '@/features/dashboard/components/manual-intervention-table'
import { OperationsTable } from '@/features/dashboard/components/operations-table'
import { RunbookDialog } from '@/features/dashboard/components/runbook-dialog'
import { useCompactElapsedTime } from '@/features/dashboard/hooks/use-compact-elapsed-time'
import {
  mapApprovalsToUi,
  mapInterventionsToUi,
  mapOperationsToUi,
} from '@/features/dashboard/mappers/dashboard-actions.mapper'
import { mapIncidentListToUi } from '@/features/dashboard/mappers/dashboard-data.mapper'
import { mapHealthQueryState } from '@/features/dashboard/mappers/dashboard-health.mapper'
import { formatPollingInterval } from '@/features/dashboard/mappers/dashboard-time.mapper'
import type { ManualIntervention } from '@/features/dashboard/types/dashboard-ui'
import { ApiError } from '@/lib/api-client'

function mutationErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 409) {
    return 'El estado cambió antes de procesar la solicitud.'
  }
  if (error instanceof ApiError && error.status === 404) {
    return 'La acción solicitada ya no existe.'
  }
  return 'No fue posible completar la acción.'
}

export function DashboardPage() {
  const [notice, setNotice] = useState<DashboardNotice | null>(null)
  const [selectedIntervention, setSelectedIntervention] =
    useState<ManualIntervention | null>(null)
  const healthQuery = useHealthQuery()
  const summaryQuery = useDashboardSummaryQuery()
  const incidentsQuery = useRecentIncidentsQuery(6)
  const operationsQuery = useDashboardOperationsQuery(5, true)
  const approvalsQuery = useDashboardApprovalsQuery(3)
  const interventionsQuery = useDashboardInterventionsQuery(3)
  const pauseMutation = usePauseScheduledActionMutation()
  const resumeMutation = useResumeScheduledActionMutation()
  const approveMutation = useApproveScheduledActionMutation()
  const rejectMutation = useRejectScheduledActionMutation()
  const retryMutation = useRetryInterventionMutation()
  const health = mapHealthQueryState(healthQuery)
  const incidents = mapIncidentListToUi(incidentsQuery.data)
  const operations = mapOperationsToUi(operationsQuery.data)
  const approvals = mapApprovalsToUi(approvalsQuery.data)
  const interventions = mapInterventionsToUi(interventionsQuery.data)
  const lastUpdatedAt = Math.max(
    summaryQuery.dataUpdatedAt,
    incidentsQuery.dataUpdatedAt,
    operationsQuery.dataUpdatedAt,
    approvalsQuery.dataUpdatedAt,
    interventionsQuery.dataUpdatedAt,
  )
  const lastUpdatedLabel = useCompactElapsedTime(lastUpdatedAt)
  const isRefreshing = [
    healthQuery,
    summaryQuery,
    incidentsQuery,
    operationsQuery,
    approvalsQuery,
    interventionsQuery,
  ].some((query) => query.isFetching)
  const pendingOperationId = pauseMutation.isPending
    ? pauseMutation.variables?.scheduledActionId ?? null
    : resumeMutation.isPending
      ? resumeMutation.variables?.scheduledActionId ?? null
      : null
  const pendingApprovalId = approveMutation.isPending
    ? approveMutation.variables?.scheduledActionId ?? null
    : rejectMutation.isPending
      ? rejectMutation.variables?.scheduledActionId ?? null
      : null

  function showNotice(tone: DashboardNotice['tone'], message: string) {
    setNotice({ id: Date.now(), tone, message })
  }

  function refreshDashboard() {
    void Promise.all([
      healthQuery.refetch(),
      summaryQuery.refetch(),
      incidentsQuery.refetch(),
      operationsQuery.refetch(),
      approvalsQuery.refetch(),
      interventionsQuery.refetch(),
    ])
  }

  function pauseOperation(id: number) {
    if (pauseMutation.isPending || resumeMutation.isPending) return
    pauseMutation.mutate(
      { scheduledActionId: id, reason: 'dashboard_manual_pause' },
      {
        onSuccess: () => showNotice('success', 'Operación pausada.'),
        onError: (error) => showNotice('error', mutationErrorMessage(error)),
      },
    )
  }

  function resumeOperation(id: number) {
    if (pauseMutation.isPending || resumeMutation.isPending) return
    resumeMutation.mutate(
      { scheduledActionId: id },
      {
        onSuccess: () => showNotice('success', 'Operación reanudada.'),
        onError: (error) => showNotice('error', mutationErrorMessage(error)),
      },
    )
  }

  function approveAction(id: number) {
    if (approveMutation.isPending || rejectMutation.isPending) return
    approveMutation.mutate(
      { scheduledActionId: id, note: 'Approved from NOC dashboard' },
      {
        onSuccess: () => showNotice('success', 'Aprobación realizada.'),
        onError: (error) => showNotice('error', mutationErrorMessage(error)),
      },
    )
  }

  function rejectAction(id: number) {
    if (approveMutation.isPending || rejectMutation.isPending) return
    rejectMutation.mutate(
      { scheduledActionId: id, note: 'Rejected from NOC dashboard' },
      {
        onSuccess: () => showNotice('success', 'Aprobación rechazada.'),
        onError: (error) => showNotice('error', mutationErrorMessage(error)),
      },
    )
  }

  function retryIntervention(item: ManualIntervention) {
    if (!item.retrySupported) {
      showNotice('info', 'El reintento no es seguro para esta intervención.')
      return
    }
    retryMutation.mutate(
      { interventionId: item.interventionId },
      {
        onSuccess: () => showNotice('success', 'Reintento iniciado.'),
        onError: (error) => showNotice('error', mutationErrorMessage(error)),
      },
    )
  }

  return (
    <div className="flex h-svh min-w-0 overflow-hidden bg-background">
      <DashboardSidebar apiState={health.api} databaseState={health.database} />
      <main className="noc-scrollbar min-w-0 flex-1 overflow-y-auto p-2">
        <div className="flex min-h-full flex-col gap-2 min-[1100px]:h-full min-[1100px]:min-h-0">
          <DashboardHeader apiState={health.api} databaseState={health.database} pollingLabel={formatPollingInterval(env.pollIntervalMs)} lastUpdatedLabel={lastUpdatedLabel} isRefreshing={isRefreshing} onRefresh={refreshDashboard} />
          <KpiGrid counts={summaryQuery.data?.counts} isLoading={summaryQuery.isPending} isError={summaryQuery.isError} isRetrying={summaryQuery.isFetching} onRetry={() => void summaryQuery.refetch()} />
          <div
            data-testid="dashboard-content-grid"
            className="dashboard-content-grid grid min-h-0 flex-1 grid-cols-1 auto-rows-[minmax(220px,auto)] gap-2 min-[1100px]:grid-cols-2 min-[1100px]:grid-rows-[minmax(320px,1.38fr)_minmax(220px,1fr)] min-[1100px]:auto-rows-auto"
          >
            <IncidentsTable incidents={incidents} hasResponse={incidentsQuery.data !== undefined} isLoading={incidentsQuery.isPending} isError={incidentsQuery.isError} isFetching={incidentsQuery.isFetching} onRetry={() => void incidentsQuery.refetch()} />
            <OperationsTable operations={operations} hasResponse={operationsQuery.data !== undefined} isLoading={operationsQuery.isPending} isError={operationsQuery.isError} isFetching={operationsQuery.isFetching} pendingId={pendingOperationId} onRetry={() => void operationsQuery.refetch()} onPause={pauseOperation} onResume={resumeOperation} />
            <ManualInterventionTable interventions={interventions} hasResponse={interventionsQuery.data !== undefined} isLoading={interventionsQuery.isPending} isError={interventionsQuery.isError} isFetching={interventionsQuery.isFetching} pendingId={retryMutation.isPending ? retryMutation.variables?.interventionId ?? null : null} onRetryList={() => void interventionsQuery.refetch()} onViewRunbook={setSelectedIntervention} onRetryIntervention={retryIntervention} />
            <ApprovalsTable approvals={approvals} hasResponse={approvalsQuery.data !== undefined} isLoading={approvalsQuery.isPending} isError={approvalsQuery.isError} isFetching={approvalsQuery.isFetching} pendingId={pendingApprovalId} onRetry={() => void approvalsQuery.refetch()} onApprove={approveAction} onReject={rejectAction} />
          </div>
        </div>
      </main>
      <DashboardNotification notice={notice} onClose={() => setNotice(null)} />
      <RunbookDialog intervention={selectedIntervention} open={selectedIntervention !== null} onOpenChange={(open) => !open && setSelectedIntervention(null)} />
    </div>
  )
}
