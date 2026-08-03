import type { LucideIcon } from 'lucide-react'

export type KpiTone =
  | 'cyan'
  | 'teal'
  | 'purple'
  | 'green'
  | 'yellow'
  | 'orange'
  | 'red'
  | 'slate'

export type KpiId =
  | 'active'
  | 'scheduled'
  | 'paused'
  | 'executing'
  | 'pending_approval'
  | 'stuck'
  | 'failed'
  | 'closed'

export type KpiDefinition = {
  id: KpiId
  label: string
  tone: KpiTone
  icon: LucideIcon
  trendPath: string
}

export type KpiItem = KpiDefinition & {
  value: number | null
}

export type Severity =
  | 'CRÍTICA'
  | 'ALTA'
  | 'ADVERTENCIA'
  | 'MEDIA'
  | 'INFORMATIVA'
  | 'SIN CLASIFICAR'

export type VisibleStatus =
  | 'ACTIVO'
  | 'PROGRAMADO'
  | 'PAUSADO'
  | 'EJECUTANDO'
  | 'PEND-APP'
  | 'TRABADO'
  | 'FALLIDO'
  | 'CERRADO'
  | 'ESPERA-CONF'
  | 'REINTENTO'
  | 'MANUAL'
  | 'CANCELADO'
  | 'EJECUTADO'
  | 'DESCONOCIDO'

export type HealthIndicatorState =
  | 'operational'
  | 'warning'
  | 'unavailable'

export type ActionKind = 'jira' | 'calls' | 'telegram' | 'email' | 'script'

export type Incident = {
  id: string
  fullId: string
  client: string
  host: string
  trigger: string
  severity: Severity
  status: VisibleStatus
  action: string | null
  time: string
  openedAt: string
  closedAt: string
  duration: string
  currentAction: string
}

export type Operation = {
  rowId: string
  scheduledActionId: number
  eventId: string
  action: string | null
  client: string
  status: VisibleStatus
  target: string
  attempts: string
  attemptCount: string
  maxAttempts: string
  createdAt: string
  activityAt: string
  control: 'Pausar' | 'Reanudar' | null
}

export type Approval = {
  scheduledActionId: number
  eventId: string
  id: string
  client: string
  objective: string
  reason: string
  time: string
  decision: 'pending' | 'approved' | 'rejected' | 'unknown'
  result: string | null
  operationState: string
  requestedAt: string
  decidedAt: string
}

export type ManualIntervention = {
  interventionId: string
  sourceType: string
  eventId: string
  client: string
  host: string
  description: string
  severity: Severity
  status: VisibleStatus
  time: string
  failureReason: string
  attempts: string
  retrySupported: boolean
  retryBlockedReason: string | null
  runbookAvailable: boolean
}

export type NavigationItem = {
  label: string
  path: string
  icon: LucideIcon
}
