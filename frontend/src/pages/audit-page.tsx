import { Form, useSearchParams } from 'react-router-dom'

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
import { useAuditLogsQuery } from '@/features/dashboard/api/dashboard-queries'
import type { AuditFilters } from '@/features/dashboard/api/dashboard-query-keys'

const LIMIT = 20
const fields = [
  { name: 'search', label: 'Buscar', type: 'text' },
  { name: 'level', label: 'Nivel', type: 'text' },
  { name: 'component', label: 'Componente', type: 'text' },
  { name: 'event_id', label: 'ID evento', type: 'text' },
  { name: 'created_from', label: 'Desde', type: 'datetime-local' },
  { name: 'created_to', label: 'Hasta', type: 'datetime-local' },
] as const

function dateInputValue(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export function AuditPage() {
  const [params, setParams] = useSearchParams()
  const filters: AuditFilters = {
    limit: LIMIT,
    offset: Number(params.get('offset')) || 0,
    search: params.get('search') || undefined,
    level: params.get('level') || undefined,
    component: params.get('component') || undefined,
    eventId: params.get('event_id') || undefined,
    createdFrom: params.get('created_from') || undefined,
    createdTo: params.get('created_to') || undefined,
  }
  const query = useAuditLogsQuery(filters)

  function submit(form: FormData) {
    const next = new URLSearchParams()
    for (const field of fields) {
      let value = String(form.get(field.name) ?? '').trim()
      if (value && field.type === 'datetime-local') {
        value = new Date(value).toISOString()
      }
      if (value) next.set(field.name, value)
    }
    setParams(next)
  }

  return (
    <div className="flex min-h-full flex-col gap-3 p-2">
      <PageHeader
        title="Auditoría"
        description="Registro de actividad operacional en modo de solo lectura."
      />
      <Form
        method="get"
        onSubmit={(event) => {
          event.preventDefault()
          submit(new FormData(event.currentTarget))
        }}
      >
        <FilterBar>
          {fields.map((field) => (
            <Field key={field.name} label={field.label}>
              <input
                className={fieldClass}
                type={field.type}
                name={field.name}
                defaultValue={
                  field.type === 'datetime-local'
                    ? dateInputValue(params.get(field.name))
                    : (params.get(field.name) ?? '')
                }
              />
            </Field>
          ))}
          <Button size="sm">Buscar</Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setParams({})}
          >
            Limpiar
          </Button>
        </FilterBar>
      </Form>
      <PageCard>
        <div className="overflow-x-auto">
          <table
            aria-label="Registros de auditoría"
            className="w-full min-w-[900px] text-left text-xs"
          >
            <thead className="text-text-muted">
              <tr className="h-9 border-b border-border-subtle">
                {['Fecha', 'Nivel', 'Componente', 'Evento', 'Acción', 'Operación', 'Mensaje', 'Contexto'].map((label) => (
                  <th key={label} className="px-3 font-normal">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="text-text-secondary">
              <TableState
                colSpan={8}
                isLoading={query.isPending}
                isError={query.isError && !query.data}
                isEmpty={Boolean(query.data && query.data.items.length === 0)}
                onRetry={() => void query.refetch()}
                emptyText="No hay registros de auditoría"
              />
              {!query.isPending && query.data?.items.map((item) => (
                <tr key={item.id} className="h-11 border-b border-border-subtle">
                  <td className="px-3 whitespace-nowrap">{item.created_at}</td>
                  <td className="px-3 uppercase">{item.level}</td>
                  <td className="px-3">{item.component}</td>
                  <td className="px-3">{item.event_id ?? '—'}</td>
                  <td className="px-3">{item.scheduled_action_id ?? '—'}</td>
                  <td className="px-3">{item.operation}</td>
                  <td className="px-3">{item.message}</td>
                  <td className="px-3">
                    {item.context && Object.keys(item.context).length
                      ? 'Contexto disponible'
                      : '—'}
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
