import { ApprovalsTable } from '@/features/dashboard/components/approvals-table'
import { DashboardHeader } from '@/features/dashboard/components/dashboard-header'
import { DashboardSidebar } from '@/features/dashboard/components/dashboard-sidebar'
import { IncidentsTable } from '@/features/dashboard/components/incidents-table'
import { KpiGrid } from '@/features/dashboard/components/kpi-grid'
import { ManualInterventionTable } from '@/features/dashboard/components/manual-intervention-table'
import { OperationsTable } from '@/features/dashboard/components/operations-table'

export function DashboardPage() {
  return (
    <div className="flex h-svh min-w-[1180px] overflow-hidden bg-background">
      <DashboardSidebar />
      <main className="noc-scrollbar min-w-0 flex-1 overflow-y-auto p-2">
        <div className="flex min-h-full flex-col gap-2">
          <DashboardHeader />
          <KpiGrid />
          <IncidentsTable />
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
