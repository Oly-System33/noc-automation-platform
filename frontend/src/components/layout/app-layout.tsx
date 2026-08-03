import { Outlet } from 'react-router-dom'

import { useHealthQuery } from '@/features/dashboard/api/dashboard-queries'
import { DashboardSidebar } from '@/features/dashboard/components/dashboard-sidebar'
import { mapHealthQueryState } from '@/features/dashboard/mappers/dashboard-health.mapper'

export function AppLayout() {
  const health = mapHealthQueryState(useHealthQuery())

  return (
    <div className="flex h-svh min-w-0 overflow-hidden bg-background">
      <DashboardSidebar apiState={health.api} databaseState={health.database} />
      <main className="noc-scrollbar min-w-0 flex-1 overflow-y-auto p-2">
        <Outlet />
      </main>
    </div>
  )
}
