import type { VisibleStatus } from '@/features/dashboard/types/dashboard-ui'

const statusLabels: Record<string, VisibleStatus> = {
  active: 'ACTIVO',
  scheduled: 'PROGRAMADO',
  paused: 'PAUSADO',
  executing: 'EJECUTANDO',
  pending_approval: 'PEND-APP',
  stuck: 'TRABADO',
  failed: 'FALLIDO',
  closed: 'CERRADO',
  waiting_confirmation: 'ESPERA-CONF',
  retry_scheduled: 'REINTENTO',
  manual_required: 'MANUAL',
  cancelled: 'CANCELADO',
  executed: 'EJECUTADO',
}

export function mapDashboardStatusToLabel(
  status: string | null | undefined,
): VisibleStatus {
  if (!status) {
    return 'DESCONOCIDO'
  }

  return statusLabels[status.trim().toLowerCase()] ?? 'DESCONOCIDO'
}
