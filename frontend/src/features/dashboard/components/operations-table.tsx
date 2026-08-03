import { Pause, Play, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ActionChannel } from '@/features/dashboard/components/action-channel'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import { StatusBadge } from '@/features/dashboard/components/status-badge'
import type { Operation } from '@/features/dashboard/types/dashboard-ui'

type OperationsTableProps = {
  operations: Operation[]
  hasResponse: boolean
  isLoading: boolean
  isError: boolean
  isFetching: boolean
  pendingId: number | null
  onRetry: () => void
  onPause: (id: number) => void
  onResume: (id: number) => void
}

export function OperationsTable(props: OperationsTableProps) {
  const showError = props.isError && !props.hasResponse
  const showEmpty = props.hasResponse && props.operations.length === 0

  return (
    <DashboardPanel
      title="Operaciones activas"
      href="/operaciones"
      footer="Ver historial de operaciones"
      footerHref="/operaciones"
      isRefreshing={props.isFetching && !props.isLoading}
      hasError={props.isError && props.hasResponse}
      onRetry={props.onRetry}
    >
      <div className="noc-scrollbar min-h-0 flex-1 overflow-auto">
        <table aria-label="Operaciones activas" className="w-full min-w-[420px] table-fixed text-left text-[10px]">
          <thead className="text-text-muted"><tr className="h-6 border-b border-border-subtle">
            <th scope="col" className="w-[17%] px-3 font-normal">Acción</th><th scope="col" className="w-[15%] px-2 font-normal">Cliente</th><th scope="col" className="w-[22%] px-2 text-center font-normal">Estado</th><th scope="col" className="w-[20%] px-2 font-normal">Objetivo</th><th scope="col" className="w-[10%] px-2 font-normal">Intentos</th><th scope="col" className="w-[16%] px-2 font-normal">Acciones</th>
          </tr></thead>
          <tbody className="text-text-secondary">
            {props.isLoading && Array.from({ length: 5 }, (_, index) => <tr key={index} data-testid="operation-skeleton" className="h-[25px] border-b border-border-subtle"><td colSpan={6} className="px-3"><span className="block h-2.5 animate-pulse rounded-sm bg-text-muted/15" /></td></tr>)}
            {showError && <tr className="h-[125px]"><td colSpan={6} className="text-center"><div role="alert" className="inline-flex items-center gap-2 text-red">No fue posible cargar las operaciones.<Button type="button" variant="outline" size="xs" onClick={props.onRetry}>Reintentar</Button></div></td></tr>}
            {showEmpty && <tr className="h-[125px]"><td colSpan={6} className="text-center text-text-muted">No hay operaciones activas</td></tr>}
            {!props.isLoading && !showError && !showEmpty && props.operations.map((operation) => {
              const pending = props.pendingId === operation.scheduledActionId
              const ControlIcon = operation.control === 'Pausar' ? Pause : Play
              return <tr key={operation.rowId} className="h-[25px] border-b border-border-subtle last:border-b-0">
                <td className="px-3"><ActionChannel action={operation.action} /></td><td className="px-2 whitespace-nowrap">{operation.client}</td><td className="px-2 text-center"><StatusBadge status={operation.status} /></td><td className="truncate px-2">{operation.target}</td><td className="px-2">{operation.attempts}</td>
                <td className="px-2">{operation.control ? <Button type="button" variant="outline" size="xs" disabled={pending} aria-busy={pending} onClick={() => operation.control === 'Pausar' ? props.onPause(operation.scheduledActionId) : props.onResume(operation.scheduledActionId)} className="h-5 min-w-[70px] rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary">{pending ? <RefreshCw aria-hidden="true" className="size-3 animate-spin" /> : <ControlIcon aria-hidden="true" className="size-3" />}{operation.control}</Button> : <span className="text-text-muted">—</span>}</td>
              </tr>
            })}
          </tbody>
        </table>
      </div>
    </DashboardPanel>
  )
}
