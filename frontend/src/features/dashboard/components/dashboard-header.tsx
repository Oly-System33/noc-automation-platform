import { Clock3, Database, RefreshCw } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { HealthIndicatorState } from '@/features/dashboard/types/dashboard-ui'

const indicatorConfig: Record<
  HealthIndicatorState,
  { className: string; apiLabel: string; databaseLabel: string }
> = {
  operational: {
    className: 'bg-green',
    apiLabel: 'operativo',
    databaseLabel: 'operativa',
  },
  warning: {
    className: 'bg-yellow',
    apiLabel: 'advertencia',
    databaseLabel: 'advertencia',
  },
  unavailable: {
    className: 'bg-red',
    apiLabel: 'no disponible',
    databaseLabel: 'no disponible',
  },
}

const controlClassName =
  'flex h-7 items-center gap-2 rounded-md border border-border bg-surface px-3 text-[10px] text-text-secondary'

type DashboardHeaderProps = {
  apiState: HealthIndicatorState
  databaseState: HealthIndicatorState
  pollingLabel: string
  lastUpdatedLabel: string
  isRefreshing: boolean
  onRefresh: () => void
}

export function DashboardHeader({
  apiState,
  databaseState,
  pollingLabel,
  lastUpdatedLabel,
  isRefreshing,
  onRefresh,
}: DashboardHeaderProps) {
  const api = indicatorConfig[apiState]
  const database = indicatorConfig[databaseState]

  return (
    <header className="flex min-h-8 items-center justify-between gap-4">
      <h1 className="text-[24px] leading-none font-semibold tracking-[-0.025em] text-text-primary">
        Dashboard principal
      </h1>
      <div className="flex shrink-0 items-center gap-2" aria-label="Estado general">
        <div className={controlClassName} aria-label={`FastAPI: ${api.apiLabel}`}>
          <span className="size-2 rounded-full border border-cyan" />
          <span>FastAPI</span>
          <span className={cn('size-2 rounded-full', api.className)} />
        </div>
        <div
          className={controlClassName}
          aria-label={`DB: ${database.databaseLabel}`}
        >
          <Database aria-hidden="true" className="size-3.5" />
          <span>DB</span>
          <span className={cn('size-2 rounded-full', database.className)} />
        </div>
        <button
          type="button"
          aria-label="Actualizar dashboard"
          disabled={isRefreshing}
          onClick={onRefresh}
          className={cn(
            controlClassName,
            'transition-colors hover:bg-surface-hover disabled:cursor-wait disabled:opacity-70',
          )}
        >
          <RefreshCw
            aria-hidden="true"
            className={cn('size-3.5', isRefreshing && 'animate-spin')}
          />
          <span>{pollingLabel}</span>
        </button>
        <div
          className={controlClassName}
          aria-label={`Última actualización: ${lastUpdatedLabel}`}
        >
          <Clock3 aria-hidden="true" className="size-3.5" />
          <span>{lastUpdatedLabel}</span>
        </div>
      </div>
    </header>
  )
}
