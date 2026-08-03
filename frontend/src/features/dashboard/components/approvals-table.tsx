import { RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import type { Approval } from '@/features/dashboard/types/dashboard-ui'

type ApprovalsTableProps = {
  approvals: Approval[]
  hasResponse: boolean
  isLoading: boolean
  isError: boolean
  isFetching: boolean
  pendingId: number | null
  onRetry: () => void
  onApprove: (id: number) => void
  onReject: (id: number) => void
}

export function ApprovalsTable(props: ApprovalsTableProps) {
  const showError = props.isError && !props.hasResponse
  const showEmpty = props.hasResponse && props.approvals.length === 0

  return <DashboardPanel title="Aprobaciones pendientes" href="/aprobaciones?status=pending" footer="Ver todas las aprobaciones" footerHref="/aprobaciones?status=pending" isRefreshing={props.isFetching && !props.isLoading} hasError={props.isError && props.hasResponse} onRetry={props.onRetry}>
    <div className="noc-scrollbar min-h-0 flex-1 overflow-auto"><table aria-label="Aprobaciones pendientes" className="w-full min-w-[510px] table-fixed text-left text-[10px]">
      <thead className="text-text-muted"><tr className="h-6 border-b border-border-subtle"><th scope="col" className="w-[13%] px-3 font-normal">ID</th><th scope="col" className="w-[12%] px-2 font-normal">Cliente</th><th scope="col" className="w-[24%] px-2 font-normal">Objetivo / Acción</th><th scope="col" className="w-[20%] px-2 font-normal">Razón</th><th scope="col" className="w-[7%] px-2 font-normal">Tiempo</th><th scope="col" className="w-[24%] px-2 font-normal">Acciones</th></tr></thead>
      <tbody className="text-text-secondary">
        {props.isLoading && Array.from({ length: 3 }, (_, index) => <tr key={index} data-testid="approval-skeleton" className="h-[45px] border-b border-border-subtle"><td colSpan={6} className="px-3"><span className="block h-2.5 animate-pulse rounded-sm bg-text-muted/15" /></td></tr>)}
        {showError && <tr className="h-[135px]"><td colSpan={6} className="text-center"><div role="alert" className="inline-flex items-center gap-2 text-red">No fue posible cargar las aprobaciones.<Button type="button" variant="outline" size="xs" onClick={props.onRetry}>Reintentar</Button></div></td></tr>}
        {showEmpty && <tr className="h-[135px]"><td colSpan={6} className="text-center text-text-muted">No hay aprobaciones pendientes</td></tr>}
        {!props.isLoading && !showError && !showEmpty && props.approvals.map((approval) => { const pending = props.pendingId === approval.scheduledActionId; return <tr key={`${approval.scheduledActionId}:${approval.objective}`} className="h-[45px] border-b border-border-subtle last:border-b-0"><td className="px-3 whitespace-nowrap">{approval.id}</td><td className="px-2 whitespace-nowrap">{approval.client}</td><td className="px-2 leading-3.5 text-text-primary">{approval.objective}</td><td className="px-2 leading-3.5">{approval.reason}</td><td className="px-2">{approval.time}</td><td className="px-2"><div className="flex gap-1.5"><Button type="button" size="xs" disabled={pending} onClick={() => props.onApprove(approval.scheduledActionId)} className="h-6 rounded-[3px] border border-primary-hover bg-primary-muted px-2 text-[9px] text-text-primary hover:bg-primary/30">{pending && <RefreshCw aria-hidden="true" className="size-3 animate-spin" />}Aprobar</Button><Button type="button" variant="outline" size="xs" disabled={pending} onClick={() => props.onReject(approval.scheduledActionId)} className="h-6 rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary">Rechazar</Button></div></td></tr> })}
      </tbody>
    </table></div>
  </DashboardPanel>
}
