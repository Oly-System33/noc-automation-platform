import { BookOpen, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import { SeverityBadge } from '@/features/dashboard/components/severity-badge'
import { manualInterventions } from '@/features/dashboard/data/dashboard-mock-data'

export function ManualInterventionTable() {
  return (
    <DashboardPanel
      title="Requiere intervención manual"
      count={manualInterventions.length}
      footer="Ver todas las intervenciones"
    >
      <div className="noc-scrollbar overflow-x-auto">
        <table
          aria-label="Requiere intervención manual"
          className="w-full min-w-[850px] table-fixed text-left text-[10px]"
        >
          <thead className="text-text-muted">
            <tr className="h-6 border-b border-border-subtle">
              <th scope="col" className="w-[11%] px-3 font-normal">ID</th>
              <th scope="col" className="w-[12%] px-2 font-normal">Cliente</th>
              <th scope="col" className="w-[28%] px-2 font-normal">Descripción</th>
              <th scope="col" className="w-[12%] px-2 text-center font-normal">Severidad</th>
              <th scope="col" className="w-[10%] px-2 font-normal">Tiempo</th>
              <th scope="col" className="w-[27%] px-2 font-normal">Acciones sugeridas</th>
            </tr>
          </thead>
          <tbody className="text-text-secondary">
            {manualInterventions.map((intervention) => (
              <tr key={intervention.id} className="h-[27px] border-b border-border-subtle last:border-b-0">
                <td className="px-3 whitespace-nowrap">{intervention.id}</td>
                <td className="px-2 whitespace-nowrap">{intervention.client}</td>
                <td className="truncate px-2 text-text-primary">{intervention.description}</td>
                <td className="px-2 text-center"><SeverityBadge severity={intervention.severity} /></td>
                <td className="px-2">{intervention.time}</td>
                <td className="px-2">
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      aria-label={`Ver runbook para ${intervention.id}`}
                      variant="outline"
                      size="xs"
                      className="h-6 min-w-[98px] rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    >
                      <BookOpen aria-hidden="true" className="size-3" />
                      Ver runbook
                    </Button>
                    <Button
                      type="button"
                      aria-label={`Reintentar flujo para ${intervention.id}`}
                      variant="outline"
                      size="xs"
                      className="h-6 min-w-[112px] rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    >
                      <RefreshCw aria-hidden="true" className="size-3" />
                      Reintentar flujo
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardPanel>
  )
}
