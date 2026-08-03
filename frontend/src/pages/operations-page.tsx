import { useState } from 'react'
import { BookOpen, Pause, Play, RefreshCw } from 'lucide-react'
import { Form, Link, useSearchParams } from 'react-router-dom'

import {
  Field,
  FilterBar,
  PageCard,
  PageHeader,
  TablePagination,
  TableState,
  fieldClass,
} from '@/components/data/page-parts'
import { Button } from '@/components/ui/button'
import {
  usePauseScheduledActionMutation,
  useResumeScheduledActionMutation,
  useRetryInterventionMutation,
} from '@/features/dashboard/api/dashboard-mutations'
import {
  useInterventionsQuery,
  useOperationsQuery,
} from '@/features/dashboard/api/dashboard-queries'
import type {
  InterventionFilters,
  OperationFilters,
} from '@/features/dashboard/api/dashboard-query-keys'
import { ActionChannel } from '@/features/dashboard/components/action-channel'
import { RunbookDialog } from '@/features/dashboard/components/runbook-dialog'
import { StatusBadge } from '@/features/dashboard/components/status-badge'
import {
  mapInterventionsToUi,
  mapOperationsToUi,
} from '@/features/dashboard/mappers/dashboard-actions.mapper'
import type { ManualIntervention } from '@/features/dashboard/types/dashboard-ui'

const LIMIT = 20
type View = 'active' | 'paused' | 'failed' | 'interventions'
const views: { id: View; label: string }[] = [
  { id: 'active', label: 'Activas' },
  { id: 'paused', label: 'Pausadas' },
  { id: 'failed', label: 'Fallidas' },
  { id: 'interventions', label: 'Intervenciones' },
]

export function OperationsPage() {
  const [params, setParams] = useSearchParams()
  const rawView = params.get('view')
  const view: View = rawView === 'paused' || rawView === 'failed' || rawView === 'interventions'
    ? rawView
    : 'active'
  const offset = Number(params.get('offset')) || 0
  const shared = {
    limit: LIMIT,
    offset,
    search: params.get('search') || undefined,
  }
  const operationFilters: OperationFilters = {
    ...shared,
    client: params.get('client') || undefined,
    status: params.get('status') || (view === 'failed' ? 'failed' : undefined),
    action: params.get('action') || undefined,
    internalState: params.get('internal_state') || (view === 'paused' ? 'paused' : undefined),
    activeOnly: view === 'active' ? true : undefined,
  }
  const interventionFilters: InterventionFilters = {
    ...shared,
    sourceType: params.get('source_type') || undefined,
    status: params.get('status') || undefined,
  }
  const operationQuery = useOperationsQuery(operationFilters, view !== 'interventions')
  const interventionQuery = useInterventionsQuery(interventionFilters, view === 'interventions')
  const operations = mapOperationsToUi(operationQuery.data)
  const interventions = mapInterventionsToUi(interventionQuery.data)
  const pause = usePauseScheduledActionMutation()
  const resume = useResumeScheduledActionMutation()
  const retry = useRetryInterventionMutation()
  const [runbook, setRunbook] = useState<ManualIntervention | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const pendingOperation = pause.isPending
    ? pause.variables?.scheduledActionId
    : resume.isPending
      ? resume.variables?.scheduledActionId
      : null

  function viewParams(nextView = view) {
    const next = new URLSearchParams()
    if (nextView !== 'active') next.set('view', nextView)
    return next
  }

  function submit(form: FormData) {
    const next = viewParams()
    const names = view === 'interventions'
      ? ['search', 'source_type', 'status']
      : ['search', 'client', 'status', 'action', 'internal_state']
    for (const name of names) {
      const value = String(form.get(name) ?? '').trim()
      if (value) next.set(name, value)
    }
    setParams(next)
  }

  function mutateOperation(id: number, control: 'Pausar' | 'Reanudar') {
    setMessage(null)
    const options = {
      onSuccess: () => setMessage(
        control === 'Pausar' ? 'Operación pausada.' : 'Operación reanudada.',
      ),
      onError: () => setMessage('No fue posible completar la acción.'),
    }
    if (control === 'Pausar') {
      pause.mutate({ scheduledActionId: id, reason: 'dashboard_manual_pause' }, options)
    } else {
      resume.mutate({ scheduledActionId: id }, options)
    }
  }

  const activeQuery = view === 'interventions' ? interventionQuery : operationQuery
  const total = activeQuery.data?.total ?? 0

  return (
    <div className="flex min-h-full flex-col gap-3 p-2">
      <PageHeader
        title="Operaciones"
        description="Control de acciones programadas e intervenciones operativas."
      />
      <nav aria-label="Vistas de operaciones" className="flex gap-1 border-b border-border-subtle">
        {views.map((item) => (
          <Link
            key={item.id}
            to={item.id === 'active' ? '/operaciones' : `/operaciones?view=${item.id}`}
            className={`border-b-2 px-3 py-2 text-xs ${view === item.id ? 'border-primary text-text-primary' : 'border-transparent text-text-muted hover:text-text-secondary'}`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <Form method="get" onSubmit={(event) => { event.preventDefault(); submit(new FormData(event.currentTarget)) }}>
        <FilterBar>
          <Field label="Buscar"><input name="search" className={fieldClass} defaultValue={shared.search} /></Field>
          {view === 'interventions' ? (
            <>
              <Field label="Origen"><input name="source_type" className={fieldClass} defaultValue={interventionFilters.sourceType} /></Field>
              <Field label="Estado"><input name="status" className={fieldClass} defaultValue={interventionFilters.status} /></Field>
            </>
          ) : (
            <>
              <Field label="Cliente"><input name="client" className={fieldClass} defaultValue={operationFilters.client} /></Field>
              <Field label="Estado"><input name="status" className={fieldClass} defaultValue={params.get('status') ?? ''} /></Field>
              <Field label="Acción"><input name="action" className={fieldClass} defaultValue={operationFilters.action} /></Field>
              <Field label="Estado interno"><input name="internal_state" className={fieldClass} defaultValue={params.get('internal_state') ?? ''} /></Field>
            </>
          )}
          <Button size="sm" type="submit">Buscar</Button>
          <Button size="sm" variant="outline" type="button" onClick={() => setParams(viewParams())}>Limpiar</Button>
        </FilterBar>
      </Form>
      {message && <p role="status" className="rounded-md border border-border bg-surface px-3 py-2 text-xs">{message}</p>}
      <PageCard>
        <div className="noc-scrollbar overflow-x-auto">
          {view === 'interventions' ? (
            <table aria-label="Intervenciones" className="w-full min-w-[1200px] text-left text-xs">
              <thead className="text-text-muted"><tr className="h-9 border-b border-border-subtle">{['ID', 'Fuente', 'Incidente', 'Cliente', 'Host', 'Descripción', 'Estado', 'Intentos', 'Bloqueo', 'Runbook', 'Acciones'].map((label) => <th key={label} className="px-3 font-normal">{label}</th>)}</tr></thead>
              <tbody className="text-text-secondary">
                <TableState colSpan={11} isLoading={interventionQuery.isPending} isError={interventionQuery.isError && !interventionQuery.data} isEmpty={Boolean(interventionQuery.data && interventions.length === 0)} onRetry={() => void interventionQuery.refetch()} emptyText="No hay intervenciones" />
                {!interventionQuery.isPending && interventions.map((item) => (
                  <tr key={item.interventionId} className="h-11 border-b border-border-subtle">
                    <td className="px-3">{item.interventionId}</td>
                    <td className="px-3">{item.sourceType}</td>
                    <td className="px-3">{item.eventId}</td>
                    <td className="px-3">{item.client}</td>
                    <td className="px-3">{item.host}</td>
                    <td className="max-w-[260px] truncate px-3" title={item.failureReason}>{item.description}</td>
                    <td className="px-3"><StatusBadge status={item.status} /></td>
                    <td className="px-3">{item.attempts}</td>
                    <td className="px-3">{item.retryBlockedReason ?? '—'}</td>
                    <td className="px-3">{item.runbookAvailable ? 'Disponible' : 'No disponible'}</td>
                    <td className="px-3"><div className="flex gap-2">
                      <Button size="xs" variant="outline" disabled={!item.runbookAvailable} title={item.runbookAvailable ? undefined : 'Runbook no disponible'} onClick={() => setRunbook(item)}><BookOpen />Runbook</Button>
                      <Button size="xs" variant="outline" disabled={!item.retrySupported || retry.isPending} title={!item.retrySupported ? item.retryBlockedReason ?? 'Reintento no disponible' : undefined} aria-describedby={!item.retrySupported ? `blocked-${item.interventionId}` : undefined} onClick={() => retry.mutate({ interventionId: item.interventionId }, { onSuccess: () => setMessage('Reintento iniciado.'), onError: () => setMessage('No fue posible iniciar el reintento.') })}><RefreshCw />Reintentar</Button>
                      {!item.retrySupported && <span id={`blocked-${item.interventionId}`} className="sr-only">{item.retryBlockedReason ?? 'Reintento no disponible'}</span>}
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table aria-label="Operaciones" className="w-full min-w-[1200px] text-left text-xs">
              <thead className="text-text-muted"><tr className="h-9 border-b border-border-subtle">{['ID', 'Incidente', 'Acción', 'Cliente', 'Estado', 'Objetivo', 'Intentos', 'Creación', 'Última actividad', 'Control'].map((label) => <th key={label} className="px-3 font-normal">{label}</th>)}</tr></thead>
              <tbody className="text-text-secondary">
                <TableState colSpan={10} isLoading={operationQuery.isPending} isError={operationQuery.isError && !operationQuery.data} isEmpty={Boolean(operationQuery.data && operations.length === 0)} onRetry={() => void operationQuery.refetch()} emptyText="No hay operaciones" />
                {!operationQuery.isPending && operations.map((item) => (
                  <tr key={item.rowId} className="h-10 border-b border-border-subtle">
                    <td className="px-3">{item.scheduledActionId}</td>
                    <td className="px-3"><Link className="hover:underline" to={`/incidentes/${encodeURIComponent(item.eventId)}`}>{item.eventId}</Link></td>
                    <td className="px-3"><ActionChannel action={item.action} /></td>
                    <td className="px-3">{item.client}</td>
                    <td className="px-3"><StatusBadge status={item.status} /></td>
                    <td className="px-3">{item.target}</td>
                    <td className="px-3">{item.attemptCount}/{item.maxAttempts}</td>
                    <td className="px-3 whitespace-nowrap">{item.createdAt}</td>
                    <td className="px-3 whitespace-nowrap">{item.activityAt}</td>
                    <td className="px-3">{item.control ? <Button size="xs" variant="outline" disabled={pendingOperation === item.scheduledActionId} onClick={() => mutateOperation(item.scheduledActionId, item.control!)}>{item.control === 'Pausar' ? <Pause /> : <Play />}{item.control}</Button> : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <TablePagination
          total={total}
          limit={LIMIT}
          offset={offset}
          disabled={activeQuery.isFetching}
          onChange={(nextOffset) => {
            const next = new URLSearchParams(params)
            if (nextOffset) next.set('offset', String(nextOffset))
            else next.delete('offset')
            setParams(next)
          }}
        />
      </PageCard>
      <RunbookDialog intervention={runbook} open={runbook !== null} onOpenChange={(open) => !open && setRunbook(null)} />
    </div>
  )
}
