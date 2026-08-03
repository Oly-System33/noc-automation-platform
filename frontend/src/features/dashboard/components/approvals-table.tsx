import { Button } from '@/components/ui/button'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import { approvals } from '@/features/dashboard/data/dashboard-static-data'

export function ApprovalsTable() {
  return (
    <DashboardPanel title="Aprobaciones pendientes" footer="Ver todas las aprobaciones">
      <div className="noc-scrollbar overflow-x-auto">
        <table
          aria-label="Aprobaciones pendientes"
          className="w-full min-w-[510px] table-fixed text-left text-[10px]"
        >
          <thead className="text-text-muted">
            <tr className="h-6 border-b border-border-subtle">
              <th scope="col" className="w-[13%] px-3 font-normal">ID</th>
              <th scope="col" className="w-[12%] px-2 font-normal">Cliente</th>
              <th scope="col" className="w-[24%] px-2 font-normal">Objetivo / Acción</th>
              <th scope="col" className="w-[20%] px-2 font-normal">Razón</th>
              <th scope="col" className="w-[7%] px-2 font-normal">Tiempo</th>
              <th scope="col" className="w-[24%] px-2 font-normal">Acciones</th>
            </tr>
          </thead>
          <tbody className="text-text-secondary">
            {approvals.map((approval) => (
              <tr key={approval.id} className="h-[45px] border-b border-border-subtle last:border-b-0">
                <td className="px-3 whitespace-nowrap">{approval.id}</td>
                <td className="px-2 whitespace-nowrap">{approval.client}</td>
                <td className="px-2 leading-3.5 text-text-primary">{approval.objective}</td>
                <td className="px-2 leading-3.5">{approval.reason}</td>
                <td className="px-2">{approval.time}</td>
                <td className="px-2">
                  <div className="flex gap-1.5">
                    <Button
                      type="button"
                      aria-label={`Aprobar solicitud ${approval.id}`}
                      size="xs"
                      className="h-6 rounded-[3px] border border-primary-hover bg-primary-muted px-2 text-[9px] text-text-primary hover:bg-primary/30"
                    >
                      Aprobar
                    </Button>
                    <Button
                      type="button"
                      aria-label={`Rechazar solicitud ${approval.id}`}
                      variant="outline"
                      size="xs"
                      className="h-6 rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    >
                      Rechazar
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
