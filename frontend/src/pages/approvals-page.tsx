import { useState } from 'react'
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
  useApproveScheduledActionMutation,
  useRejectScheduledActionMutation,
} from '@/features/dashboard/api/dashboard-mutations'
import { useApprovalsQuery } from '@/features/dashboard/api/dashboard-queries'
import type { ApprovalFilters } from '@/features/dashboard/api/dashboard-query-keys'
import { mapApprovalsToUi } from '@/features/dashboard/mappers/dashboard-actions.mapper'

const LIMIT = 20
const statuses: { id: ApprovalFilters['status']; label: string }[] = [
  { id: 'pending', label: 'Pendientes' },
  { id: 'approved', label: 'Aprobadas' },
  { id: 'rejected', label: 'Rechazadas' },
  { id: 'all', label: 'Todas' },
]

export function ApprovalsPage() {
  const [params, setParams] = useSearchParams()
  const rawStatus = params.get('status')
  const status: ApprovalFilters['status'] = rawStatus === 'approved' || rawStatus === 'rejected' || rawStatus === 'all'
    ? rawStatus
    : 'pending'
  const filters: ApprovalFilters = {
    status,
    limit: LIMIT,
    offset: Number(params.get('offset')) || 0,
    search: params.get('search') || undefined,
    client: params.get('client') || undefined,
  }
  const query = useApprovalsQuery(filters)
  const approvals = mapApprovalsToUi(query.data)
  const approve = useApproveScheduledActionMutation()
  const reject = useRejectScheduledActionMutation()
  const [message, setMessage] = useState<string | null>(null)
  const pendingId = approve.isPending
    ? approve.variables?.scheduledActionId
    : reject.isPending
      ? reject.variables?.scheduledActionId
      : null

  function base(nextStatus = status) {
    const next = new URLSearchParams()
    if (nextStatus !== 'pending') next.set('status', nextStatus)
    return next
  }

  function decide(id: number, decision: 'approve' | 'reject') {
    const mutation = decision === 'approve' ? approve : reject
    mutation.mutate(
      { scheduledActionId: id, note: `${decision}d from NOC dashboard` },
      {
        onSuccess: () => setMessage(
          decision === 'approve' ? 'Aprobación realizada.' : 'Aprobación rechazada.',
        ),
        onError: () => setMessage('No fue posible completar la decisión.'),
      },
    )
  }

  return (
    <div className="flex min-h-full flex-col gap-3 p-2">
      <PageHeader title="Aprobaciones" description="Decisiones pendientes e historial de aprobaciones." />
      <nav aria-label="Estados de aprobación" className="flex gap-1 border-b border-border-subtle">
        {statuses.map((item) => (
          <Link
            key={item.id}
            to={item.id === 'pending' ? '/aprobaciones' : `/aprobaciones?status=${item.id}`}
            className={`border-b-2 px-3 py-2 text-xs ${status === item.id ? 'border-primary text-text-primary' : 'border-transparent text-text-muted'}`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <Form
        method="get"
        onSubmit={(event) => {
          event.preventDefault()
          const data = new FormData(event.currentTarget)
          const next = base()
          for (const name of ['search', 'client']) {
            const value = String(data.get(name) ?? '').trim()
            if (value) next.set(name, value)
          }
          setParams(next)
        }}
      >
        <FilterBar>
          <Field label="Buscar"><input name="search" className={fieldClass} defaultValue={filters.search} /></Field>
          <Field label="Cliente"><input name="client" className={fieldClass} defaultValue={filters.client} /></Field>
          <Button size="sm">Buscar</Button>
          <Button type="button" size="sm" variant="outline" onClick={() => setParams(base())}>Limpiar</Button>
        </FilterBar>
      </Form>
      {message && <p role="status" className="rounded-md border border-border bg-surface px-3 py-2 text-xs">{message}</p>}
      <PageCard>
        <div className="overflow-x-auto">
          <table aria-label="Aprobaciones" className="w-full min-w-[1200px] text-left text-xs">
            <thead className="text-text-muted"><tr className="h-9 border-b border-border-subtle">{['ID', 'Incidente', 'Cliente', 'Objetivo / Acción', 'Razón', 'Estado', 'Decisión', 'Solicitud', 'Resolución', 'Resultado', 'Acciones'].map((label) => <th key={label} className="px-3 font-normal">{label}</th>)}</tr></thead>
            <tbody className="text-text-secondary">
              <TableState colSpan={11} isLoading={query.isPending} isError={query.isError && !query.data} isEmpty={Boolean(query.data && approvals.length === 0)} onRetry={() => void query.refetch()} emptyText="No hay aprobaciones" />
              {!query.isPending && approvals.map((item) => (
                <tr key={item.scheduledActionId} className="h-11 border-b border-border-subtle">
                  <td className="px-3">{item.id}</td>
                  <td className="px-3"><Link className="hover:underline" to={`/incidentes/${encodeURIComponent(item.eventId)}`}>{item.eventId}</Link></td>
                  <td className="px-3">{item.client}</td>
                  <td className="px-3">{item.objective}</td>
                  <td className="px-3">{item.reason}</td>
                  <td className="px-3">{item.operationState}</td>
                  <td className="px-3">{item.decision}</td>
                  <td className="px-3 whitespace-nowrap">{item.requestedAt}</td>
                  <td className="px-3 whitespace-nowrap">{item.decidedAt}</td>
                  <td className="px-3">{item.result ?? '—'}</td>
                  <td className="px-3">
                    {item.decision === 'pending' ? (
                      <div className="flex gap-2">
                        <Button size="xs" disabled={pendingId === item.scheduledActionId} onClick={() => decide(item.scheduledActionId, 'approve')}>Aprobar</Button>
                        <Button size="xs" variant="outline" disabled={pendingId === item.scheduledActionId} onClick={() => decide(item.scheduledActionId, 'reject')}>Rechazar</Button>
                      </div>
                    ) : `Solo lectura: ${item.result ?? item.decision}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <TablePagination
          total={query.data?.total ?? 0}
          limit={LIMIT}
          offset={filters.offset}
          disabled={query.isFetching}
          onChange={(offset) => {
            const next = new URLSearchParams(params)
            if (offset) next.set('offset', String(offset))
            else next.delete('offset')
            setParams(next)
          }}
        />
      </PageCard>
    </div>
  )
}
