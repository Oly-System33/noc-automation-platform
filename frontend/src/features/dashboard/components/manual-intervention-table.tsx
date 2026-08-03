import { BookOpen, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { DashboardPanel } from '@/features/dashboard/components/dashboard-panel'
import { SeverityBadge } from '@/features/dashboard/components/severity-badge'
import type { ManualIntervention } from '@/features/dashboard/types/dashboard-ui'

type ManualInterventionTableProps = {
  interventions: ManualIntervention[]
  hasResponse: boolean
  isLoading: boolean
  isError: boolean
  isFetching: boolean
  pendingId: string | null
  onRetryList: () => void
  onViewRunbook: (item: ManualIntervention) => void
  onRetryIntervention: (item: ManualIntervention) => void
}

export function ManualInterventionTable(props: ManualInterventionTableProps) {
  const showError = props.isError && !props.hasResponse
  const showEmpty = props.hasResponse && props.interventions.length === 0

  return <DashboardPanel title="Requiere intervención manual" href="/operaciones?view=interventions" count={props.hasResponse ? props.interventions.length : undefined} footer="Ver todas las intervenciones" footerHref="/operaciones?view=interventions" isRefreshing={props.isFetching && !props.isLoading} hasError={props.isError && props.hasResponse} onRetry={props.onRetryList}>
    <div className="noc-scrollbar min-h-0 flex-1 overflow-auto"><table aria-label="Requiere intervención manual" className="w-full min-w-[850px] table-fixed text-left text-[10px]">
      <thead className="text-text-muted"><tr className="h-6 border-b border-border-subtle"><th scope="col" className="w-[11%] px-3 font-normal">ID</th><th scope="col" className="w-[12%] px-2 font-normal">Cliente</th><th scope="col" className="w-[28%] px-2 font-normal">Descripción</th><th scope="col" className="w-[12%] px-2 text-center font-normal">Severidad</th><th scope="col" className="w-[10%] px-2 font-normal">Tiempo</th><th scope="col" className="w-[27%] px-2 font-normal">Acciones sugeridas</th></tr></thead>
      <tbody className="text-text-secondary">
        {props.isLoading && Array.from({ length: 3 }, (_, index) => <tr key={index} data-testid="intervention-skeleton" className="h-[27px] border-b border-border-subtle"><td colSpan={6} className="px-3"><span className="block h-2.5 animate-pulse rounded-sm bg-text-muted/15" /></td></tr>)}
        {showError && <tr className="h-[81px]"><td colSpan={6} className="text-center"><div role="alert" className="inline-flex items-center gap-2 text-red">No fue posible cargar las intervenciones.<Button type="button" variant="outline" size="xs" onClick={props.onRetryList}>Reintentar</Button></div></td></tr>}
        {showEmpty && <tr className="h-[81px]"><td colSpan={6} className="text-center text-text-muted">No hay intervenciones manuales pendientes</td></tr>}
        {!props.isLoading && !showError && !showEmpty && props.interventions.map((item) => { const pending = props.pendingId === item.interventionId; const retryBlocked = !item.retrySupported; return <tr key={item.interventionId} className="h-[27px] border-b border-border-subtle last:border-b-0"><td className="px-3 whitespace-nowrap" title={item.interventionId}>{item.eventId}</td><td className="px-2 whitespace-nowrap">{item.client}</td><td className="truncate px-2 text-text-primary" title={item.failureReason}>{item.description}</td><td className="px-2 text-center"><SeverityBadge severity={item.severity} /></td><td className="px-2">{item.time}</td><td className="px-2"><div className="flex gap-2"><Button type="button" variant="outline" size="xs" disabled={!item.runbookAvailable} title={item.runbookAvailable ? undefined : 'Runbook no disponible'} onClick={() => props.onViewRunbook(item)} className="h-6 min-w-[98px] rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary"><BookOpen aria-hidden="true" className="size-3" />Ver runbook</Button><Button type="button" variant="outline" size="xs" disabled={pending} aria-disabled={retryBlocked} title={retryBlocked ? item.retryBlockedReason ?? 'Reintento no disponible' : undefined} aria-describedby={retryBlocked ? `retry-blocked-${item.interventionId}` : undefined} aria-label={item.retrySupported ? `Reintentar flujo ${item.interventionId}` : `Reintento no seguro ${item.interventionId}`} onClick={() => props.onRetryIntervention(item)} className="h-6 min-w-[112px] rounded-[3px] border-border bg-transparent px-2 text-[9px] text-text-secondary hover:bg-surface-hover hover:text-text-primary">{pending ? <RefreshCw aria-hidden="true" className="size-3 animate-spin" /> : <RefreshCw aria-hidden="true" className="size-3" />}Reintentar flujo</Button>{retryBlocked && <span id={`retry-blocked-${item.interventionId}`} className="sr-only">{item.retryBlockedReason ?? 'Reintento no disponible'}</span>}</div></td></tr> })}
      </tbody>
    </table></div>
  </DashboardPanel>
}
