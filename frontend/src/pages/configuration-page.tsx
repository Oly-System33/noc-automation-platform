import { env } from '@/config/env'
import { PageCard, PageHeader } from '@/components/data/page-parts'
import { Button } from '@/components/ui/button'
import { useHealthQuery, useOperationalConfigurationQuery } from '@/features/dashboard/api/dashboard-queries'

function display(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === '') return 'No informado'
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  return String(value)
}

export function ConfigurationPage() {
  const health = useHealthQuery()
  const configuration = useOperationalConfigurationQuery()
  const values = configuration.data ? [
    ['Worker habilitado', configuration.data.worker.enabled],
    ['Worker ejecutándose', configuration.data.worker.running],
    ['Worker listo', configuration.data.worker.ready],
    ['Intervalo worker (s)', configuration.data.worker.poll_interval_seconds],
    ['Tamaño de lote', configuration.data.worker.batch_size],
    ['Timeout de procesamiento (min)', configuration.data.worker.processing_timeout_minutes],
    ['Intentos máximos', configuration.data.worker.max_attempts],
    ['Runbooks disponibles', configuration.data.runbooks.available],
    ['Cantidad de runbooks', configuration.data.runbooks.count],
    ['Runbooks en caché', configuration.data.runbooks.cache_count],
    ['Última recarga', configuration.data.runbooks.last_reload],
  ] as const : []
  return <div className="flex min-h-full flex-col gap-3 p-2"><PageHeader title="Configuración" description="Valores operativos públicos y estado de conectividad. No se muestran secretos." /><PageCard><h2 className="border-b border-border-subtle px-4 py-3 text-sm font-medium">Conectividad</h2><dl className="grid gap-4 p-4 text-xs sm:grid-cols-2 lg:grid-cols-3"><div><dt className="text-text-muted">API</dt><dd className="mt-1 text-text-primary">{health.data?.status ?? (health.isError ? 'unavailable' : 'Cargando')}</dd></div><div><dt className="text-text-muted">Base de datos</dt><dd className="mt-1 text-text-primary">{health.data?.database ?? 'No informado'}</dd></div><div><dt className="text-text-muted">URL pública de API</dt><dd className="mt-1 break-all text-text-primary">{env.apiBaseUrl}</dd></div><div><dt className="text-text-muted">Intervalo del dashboard</dt><dd className="mt-1 text-text-primary">{env.pollIntervalMs} ms</dd></div></dl></PageCard><PageCard><div className="flex items-center justify-between border-b border-border-subtle px-4 py-3"><h2 className="text-sm font-medium">Configuración operacional</h2>{configuration.isError && <Button size="xs" variant="outline" onClick={() => void configuration.refetch()}>Reintentar</Button>}</div>{configuration.isPending ? <div aria-label="Cargando configuración" className="m-4 h-24 animate-pulse rounded bg-text-muted/15" /> : configuration.isError ? <p role="alert" className="p-4 text-xs text-red">No fue posible cargar la configuración operacional.</p> : <dl className="grid gap-4 p-4 text-xs sm:grid-cols-2 lg:grid-cols-3">{values.map(([label, value]) => <div key={label}><dt className="text-text-muted">{label}</dt><dd className="mt-1 text-text-primary">{display(value)}</dd></div>)}</dl>}</PageCard></div>
}
