import { Ellipsis } from 'lucide-react'

import { ActionChannel } from '@/features/dashboard/components/action-channel'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import { SeverityBadge } from '@/features/dashboard/components/severity-badge'
import { StatusBadge } from '@/features/dashboard/components/status-badge'
import { incidents } from '@/features/dashboard/data/dashboard-mock-data'

export function IncidentsTable() {
  return (
    <DashboardPanel title="Incidentes recientes">
      <div className="noc-scrollbar overflow-x-auto">
        <table
          aria-label="Incidentes recientes"
          className="w-full min-w-[900px] table-fixed text-left text-[10px]"
        >
          <thead className="text-text-muted">
            <tr className="h-6 border-b border-border-subtle">
              <th scope="col" className="w-[11%] px-3 font-normal">ID</th>
              <th scope="col" className="w-[11%] px-2 font-normal">Cliente</th>
              <th scope="col" className="w-[11%] px-2 font-normal">Host</th>
              <th scope="col" className="w-[18%] px-2 font-normal">Trigger</th>
              <th scope="col" className="w-[12%] px-2 text-center font-normal">Severidad</th>
              <th scope="col" className="w-[13%] px-2 text-center font-normal">Estado</th>
              <th scope="col" className="w-[14%] px-2 font-normal">Acción actual</th>
              <th scope="col" className="w-[7%] px-2 font-normal">Tiempo</th>
              <th scope="col" className="w-[3%] px-2"><span className="sr-only">Menú</span></th>
            </tr>
          </thead>
          <tbody className="text-text-secondary">
            {incidents.map((incident) => (
              <tr
                key={incident.id}
                className="h-[25px] border-b border-border-subtle last:border-b-0 hover:bg-surface-hover/50"
              >
                <td className="px-3 whitespace-nowrap">{incident.id}</td>
                <td className="px-2 whitespace-nowrap">{incident.client}</td>
                <td className="px-2 whitespace-nowrap">{incident.host}</td>
                <td className="truncate px-2 text-text-primary">{incident.trigger}</td>
                <td className="px-2 text-center"><SeverityBadge severity={incident.severity} /></td>
                <td className="px-2 text-center"><StatusBadge status={incident.status} /></td>
                <td className="px-2"><ActionChannel action={incident.action} /></td>
                <td className="px-2 whitespace-nowrap">{incident.time}</td>
                <td className="px-2 text-right">
                  <button
                    type="button"
                    aria-label={`Más opciones para incidente ${incident.id}`}
                    className="inline-flex size-5 items-center justify-center rounded-sm text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                  >
                    <Ellipsis aria-hidden="true" className="size-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardPanel>
  )
}
