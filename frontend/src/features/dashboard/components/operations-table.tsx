import { Pause, Play } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ActionChannel } from '@/features/dashboard/components/action-channel'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import { StatusBadge } from '@/features/dashboard/components/status-badge'
import { operations } from '@/features/dashboard/data/dashboard-static-data'

export function OperationsTable() {
  return (
    <DashboardPanel title="Operaciones activas" footer="Ver historial de operaciones">
      <div className="noc-scrollbar overflow-x-auto">
        <table
          aria-label="Operaciones activas"
          className="w-full min-w-[420px] table-fixed text-left text-[10px]"
        >
          <thead className="text-text-muted">
            <tr className="h-6 border-b border-border-subtle">
              <th scope="col" className="w-[17%] px-3 font-normal">Acción</th>
              <th scope="col" className="w-[15%] px-2 font-normal">Cliente</th>
              <th scope="col" className="w-[22%] px-2 text-center font-normal">Estado</th>
              <th scope="col" className="w-[20%] px-2 font-normal">Objetivo</th>
              <th scope="col" className="w-[10%] px-2 font-normal">Intentos</th>
              <th scope="col" className="w-[16%] px-2 font-normal">Acciones</th>
            </tr>
          </thead>
          <tbody className="text-text-secondary">
            {operations.map((operation) => {
              const ControlIcon = operation.control === 'Pausar' ? Pause : Play
              return (
                <tr key={operation.action} className="h-[25px] border-b border-border-subtle last:border-b-0">
                  <td className="px-3"><ActionChannel action={operation.action} /></td>
                  <td className="px-2 whitespace-nowrap">{operation.client}</td>
                  <td className="px-2 text-center"><StatusBadge status={operation.status} /></td>
                  <td className="truncate px-2">{operation.target}</td>
                  <td className="px-2">{operation.attempts}</td>
                  <td className="px-2">
                    <Button
                      type="button"
                      aria-label={`${operation.control} ${operation.action} de ${operation.client}`}
                      variant="outline"
                      size="xs"
                      className="h-5 min-w-[70px] rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    >
                      <ControlIcon aria-hidden="true" className="size-3" />
                      {operation.control}
                    </Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </DashboardPanel>
  )
}
