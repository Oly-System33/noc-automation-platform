import { Ellipsis } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ActionChannel } from '@/features/dashboard/components/action-channel'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import { SeverityBadge } from '@/features/dashboard/components/severity-badge'
import { StatusBadge } from '@/features/dashboard/components/status-badge'
import type { Incident } from '@/features/dashboard/types/dashboard-ui'

type IncidentsTableProps = {
  incidents: Incident[]
  hasResponse: boolean
  isLoading: boolean
  isError: boolean
  isFetching: boolean
  onRetry: () => void
}

const ROW_COUNT = 6

function LoadingRows() {
  return Array.from({ length: ROW_COUNT }, (_, index) => (
    <tr
      key={index}
      data-testid="incident-skeleton"
      className="h-[25px] border-b border-border-subtle last:border-b-0"
    >
      <td colSpan={9} className="px-3">
        <span className="block h-2.5 animate-pulse rounded-sm bg-text-muted/15" />
      </td>
    </tr>
  ))
}

export function IncidentsTable({
  incidents,
  hasResponse,
  isLoading,
  isError,
  isFetching,
  onRetry,
}: IncidentsTableProps) {
  const showError = isError && !hasResponse
  const showEmpty = hasResponse && incidents.length === 0
  const fillerRows = Math.max(0, ROW_COUNT - incidents.length)

  return (
    <DashboardPanel
      title="Incidentes recientes"
      isRefreshing={isFetching && !isLoading}
      hasError={isError && hasResponse}
      onRetry={onRetry}
    >
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
            {isLoading && <LoadingRows />}
            {showError && (
              <tr className="h-[150px]">
                <td colSpan={9} className="px-3 text-center">
                  <div role="alert" className="inline-flex items-center gap-3 text-red">
                    No fue posible cargar los incidentes
                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      disabled={isFetching}
                      onClick={onRetry}
                      className="h-6 rounded-[3px] border-red/50 bg-transparent px-2 text-[9px] text-text-primary hover:bg-red/10"
                    >
                      Reintentar
                    </Button>
                  </div>
                </td>
              </tr>
            )}
            {showEmpty && (
              <tr className="h-[150px]">
                <td colSpan={9} className="px-3 text-center text-text-muted">
                  No hay incidentes recientes
                </td>
              </tr>
            )}
            {!isLoading && !showError && !showEmpty && incidents.map((incident) => (
              <tr
                key={incident.fullId}
                className="h-[25px] border-b border-border-subtle last:border-b-0 hover:bg-surface-hover/50"
              >
                <td
                  className="px-3 whitespace-nowrap"
                  title={incident.fullId}
                  aria-label={`Incidente ${incident.fullId}`}
                >
                  {incident.id}
                </td>
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
                    aria-label={`Más opciones para incidente ${incident.fullId}`}
                    className="inline-flex size-5 items-center justify-center rounded-sm text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                  >
                    <Ellipsis aria-hidden="true" className="size-4" />
                  </button>
                </td>
              </tr>
            ))}
            {!isLoading && !showError && !showEmpty && Array.from(
              { length: fillerRows },
              (_, index) => (
                <tr
                  key={`filler-${index}`}
                  aria-hidden="true"
                  className="h-[25px] border-b border-border-subtle last:border-b-0"
                >
                  <td colSpan={9} />
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </DashboardPanel>
  )
}
