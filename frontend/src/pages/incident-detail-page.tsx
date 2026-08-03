import { Link, useParams } from 'react-router-dom'

import { PageCard, PageHeader } from '@/components/data/page-parts'
import { Button } from '@/components/ui/button'
import { useIncidentDetailQuery } from '@/features/dashboard/api/dashboard-queries'
import type { IncidentDetailRecord } from '@/features/dashboard/api/dashboard-api.types'

const sections: { key: 'operations' | 'actions' | 'call_attempts' | 'approvals' | 'interventions' | 'audit_logs'; label: string }[] = [{ key: 'operations', label: 'Operaciones' }, { key: 'actions', label: 'Acciones' }, { key: 'call_attempts', label: 'Intentos' }, { key: 'approvals', label: 'Aprobaciones' }, { key: 'interventions', label: 'Intervenciones' }, { key: 'audit_logs', label: 'Auditoría' }]

function recordLabel(record: IncidentDetailRecord) {
  return record.message ?? record.action ?? record.operation ?? record.result ?? record.failure_reason ?? record.reason ?? record.decision ?? record.status ?? record.state ?? record.operation_state ?? 'Registro operativo'
}

export function IncidentDetailPage() {
  const eventId = useParams().eventId ?? ''
  const query = useIncidentDetailQuery(eventId)
  if (query.isPending) return <div className="p-4" aria-label="Cargando incidente"><span className="block h-24 animate-pulse rounded-md bg-surface" /></div>
  if (query.isError || !query.data) return <div className="flex h-full items-center justify-center"><div role="alert" className="text-center text-sm text-red">No fue posible cargar el incidente.<div className="mt-3"><Button size="sm" variant="outline" onClick={() => void query.refetch()}>Reintentar</Button></div></div></div>
  const incident = query.data
  return <div className="flex flex-col gap-3 p-2"><PageHeader title={`Incidente ${incident.event_id}`} description="Detalle operativo y registros relacionados seguros." actions={<Button asChild size="sm" variant="outline"><Link to="/incidentes">Volver</Link></Button>} /><PageCard><dl className="grid gap-3 p-4 text-xs sm:grid-cols-2 lg:grid-cols-4">{[['Cliente', incident.client], ['Host', incident.host], ['Trigger', incident.trigger], ['Grupo', incident.trigger_group], ['Severidad', incident.severity], ['Estado', incident.display_status], ['Abierto', incident.opened_at], ['Cerrado', incident.closed_at], ['Duración', incident.duration], ['Actualizado', incident.updated_at], ['Acción actual', incident.current_action]].map(([label, value]) => <div key={label}><dt className="text-text-muted">{label}</dt><dd className="mt-1 text-text-primary">{value || '—'}</dd></div>)}</dl></PageCard>{sections.map((section) => <PageCard key={section.key}><h2 className="border-b border-border-subtle px-3 py-2 text-sm font-medium">{section.label}</h2>{query.data[section.key].length === 0 ? <p className="p-3 text-xs text-text-muted">Sin registros relacionados</p> : <ul className="divide-y divide-border-subtle">{query.data[section.key].map((record, index) => <li key={`${record.id ?? record.action_id ?? record.call_attempt_id ?? record.audit_log_id ?? index}:${index}`} className="flex justify-between gap-3 p-3 text-xs"><span>{recordLabel(record)}</span><span className="text-text-muted">{record.created_at ?? record.activity_at ?? record.updated_at ?? record.started_at ?? record.completed_at ?? record.attempted_at ?? record.requested_at ?? record.decided_at ?? record.detected_at ?? '—'}</span></li>)}</ul>}</PageCard>)}</div>
}
