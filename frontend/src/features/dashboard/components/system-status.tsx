import { ChevronUp, Server } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { HealthIndicatorState } from '@/features/dashboard/types/dashboard-ui'

const stateConfig: Record<
  HealthIndicatorState,
  { dot: string; text: string; label: string }
> = {
  operational: { dot: 'bg-green', text: 'text-green', label: 'OK' },
  warning: { dot: 'bg-yellow', text: 'text-yellow', label: '...' },
  unavailable: { dot: 'bg-red', text: 'text-red', label: 'ERROR' },
}

type SystemStatusProps = {
  apiState: HealthIndicatorState
  databaseState: HealthIndicatorState
}

export function SystemStatus({
  apiState,
  databaseState,
}: SystemStatusProps) {
  const api = stateConfig[apiState]
  const database = stateConfig[databaseState]
  const overall =
    apiState === 'unavailable' || databaseState === 'unavailable'
      ? stateConfig.unavailable
      : apiState === 'warning' || databaseState === 'warning'
        ? stateConfig.warning
        : stateConfig.operational

  return (
    <section className="rounded-md border border-border bg-surface/70 p-3 text-[10px]">
      <div className="mb-3 flex items-center justify-between text-text-secondary">
        <div className="flex items-center gap-2">
          <span className={cn('size-2 rounded-full', overall.dot)} />
          <h2 className="font-normal">Estado del sistema</h2>
        </div>
        <ChevronUp aria-hidden="true" className="size-3.5" />
      </div>
      <div className="space-y-2.5 text-text-secondary">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Server aria-hidden="true" className="size-3.5" />
            API
          </span>
          <span className={cn('flex items-center gap-1.5', api.text)}>
            <span className={cn('size-2 rounded-full', api.dot)} /> {api.label}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <span className={cn('size-2 rounded-full', database.dot)} />
            PostgreSQL
          </span>
          <span className={cn('flex items-center gap-1.5', database.text)}>
            <span className={cn('size-2 rounded-full', database.dot)} />{' '}
            {database.label}
          </span>
        </div>
      </div>
    </section>
  )
}
