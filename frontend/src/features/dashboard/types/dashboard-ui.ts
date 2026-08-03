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

export type KpiItem = {
  id: string
  label: string
  value: number
  tone: KpiTone
  icon: LucideIcon
  trendPath: string
}

export type Severity = 'CRÍTICA' | 'ALTA' | 'ADVERTENCIA' | 'MEDIA'

export type VisibleStatus =
  | 'ACTIVO'
  | 'EJECUTANDO'
  | 'PROGRAMADO'
  | 'PAUSADO'
  | 'PEND-APP'
  | 'TRABADO'

export type ActionKind = 'jira' | 'calls' | 'telegram' | 'email' | 'script'

export type Incident = {
  id: string
  client: string
  host: string
  trigger: string
  severity: Severity
  status: VisibleStatus
  action: ActionKind
  time: string
}

export type Operation = {
  action: ActionKind
  client: string
  status: VisibleStatus
  target: string
  attempts: string
  control: 'Pausar' | 'Reanudar'
}

export type Approval = {
  id: string
  client: string
  objective: string
  reason: string
  time: string
}

export type ManualIntervention = {
  id: string
  client: string
  description: string
  severity: Severity
  time: string
}

export type NavigationItem = {
  label: string
  path: string
  icon: LucideIcon
}
