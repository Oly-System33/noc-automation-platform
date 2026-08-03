import type { HealthResponse } from '@/features/dashboard/api/dashboard-api.types'
import type { HealthIndicatorState } from '@/features/dashboard/types/dashboard-ui'

type HealthQueryState = {
  data?: HealthResponse
  isPending: boolean
  isFetching: boolean
  isError: boolean
}

export type SystemHealthState = {
  api: HealthIndicatorState
  database: HealthIndicatorState
}

export function mapHealthQueryState({
  data,
  isPending,
  isFetching,
  isError,
}: HealthQueryState): SystemHealthState {
  if (isPending || isFetching) {
    return { api: 'warning', database: 'warning' }
  }

  if (isError || !data) {
    return { api: 'unavailable', database: 'warning' }
  }

  if (data.status !== 'ok') {
    return { api: 'unavailable', database: 'unavailable' }
  }

  return {
    api: 'operational',
    database: data.database === 'ok' ? 'operational' : 'unavailable',
  }
}
