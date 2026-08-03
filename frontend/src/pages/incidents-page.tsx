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
import { useIncidentsQuery } from '@/features/dashboard/api/dashboard-queries'
import type { IncidentFilters } from '@/features/dashboard/api/dashboard-query-keys'
import { SeverityBadge } from '@/features/dashboard/components/severity-badge'
import { StatusBadge } from '@/features/dashboard/components/status-badge'
import { mapIncidentListToUi } from '@/features/dashboard/mappers/dashboard-data.mapper'

const LIMIT = 20
const filterNames = ['search', 'client', 'severity', 'status', 'incident_status']

export function IncidentsPage() {
  const [params, setParams] = useSearchParams()
  const filters: IncidentFilters = {
    limit: LIMIT,
    offset: Number(params.get('offset')) || 0,
    search: params.get('search') || undefined,
    client: params.get('client') || undefined,
    severity: params.get('severity') || undefined,
    status: params.get('status') || undefined,
    incidentStatus: params.get('incident_status') || undefined,
  }
  const query = useIncidentsQuery(filters)
  const incidents = mapIncidentListToUi(query.data)

  function submit(form: FormData) {
    const next = new URLSearchParams()
    for (const name of filterNames) {
      const value = String(form.get(name) ?? '').trim()
      if (value) next.set(name, value)
    }
    setParams(next)
  }

  return (
    <div className="flex min-h-full flex-col gap-3 p-2">
      <PageHeader
        title="Incidentes"
        description="Consulta y seguimiento de eventos operativos."
      />
      <Form
        method="get"
        onSubmit={(event) => {
          event.preventDefault()
          submit(new FormData(event.currentTarget))
        }}
      >
        <FilterBar>
          <Field label="Buscar"><input className={fieldClass} name="search" defaultValue={filters.search} placeholder="ID, host o trigger" /></Field>
          <Field label="Cliente"><input className={fieldClass} name="client" defaultValue={filters.client} /></Field>
          <Field label="Severidad"><input className={fieldClass} name="severity" defaultValue={filters.severity} /></Field>
          <Field label="Estado visible"><input className={fieldClass} name="status" defaultValue={filters.status} /></Field>
          <Field label="Estado incidente"><input className={fieldClass} name="incident_status" defaultValue={filters.incidentStatus} /></Field>
          <Button size="sm" type="submit">Buscar</Button>
          <Button size="sm" variant="outline" type="button" onClick={() => setParams({})}>Limpiar</Button>
        </FilterBar>
      </Form>
      <PageCard>
        <div className="noc-scrollbar overflow-x-auto">
          <table aria-label="Incidentes" className="w-full min-w-[1250px] text-left text-xs">
            <thead className="text-text-muted">
              <tr className="h-9 border-b border-border-subtle">
                {['ID', 'Cliente', 'Host', 'Trigger', 'Severidad', 'Estado', 'Apertura', 'Cierre', 'Duración', 'Acción actual'].map((label) => (
                  <th key={label} className="px-3 font-normal">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="text-text-secondary">
              <TableState
                colSpan={10}
                isLoading={query.isPending}
                isError={query.isError && !query.data}
                isEmpty={Boolean(query.data && incidents.length === 0)}
                onRetry={() => void query.refetch()}
                emptyText="No hay incidentes para estos filtros"
              />
              {!query.isPending && incidents.map((item) => (
                <tr key={item.fullId} className="h-10 border-b border-border-subtle hover:bg-surface-hover/50">
                  <td className="px-3"><Link className="text-text-primary hover:underline" to={`/incidentes/${encodeURIComponent(item.fullId)}`}>{item.fullId}</Link></td>
                  <td className="px-3">{item.client}</td>
                  <td className="px-3">{item.host}</td>
                  <td className="max-w-[260px] truncate px-3">{item.trigger}</td>
                  <td className="px-3"><SeverityBadge severity={item.severity} /></td>
                  <td className="px-3"><StatusBadge status={item.status} /></td>
                  <td className="px-3 whitespace-nowrap">{item.openedAt}</td>
                  <td className="px-3 whitespace-nowrap">{item.closedAt}</td>
                  <td className="px-3">{item.duration}</td>
                  <td className="px-3">{item.currentAction}</td>
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
