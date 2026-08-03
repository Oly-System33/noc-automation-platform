import type { Severity } from '@/features/dashboard/types/dashboard-ui'

const severityLabels: Record<string, Severity> = {
  critical: 'CRÍTICA',
  disaster: 'CRÍTICA',
  critico: 'CRÍTICA',
  critica: 'CRÍTICA',
  high: 'ALTA',
  alta: 'ALTA',
  warning: 'ADVERTENCIA',
  advertencia: 'ADVERTENCIA',
  average: 'MEDIA',
  medium: 'MEDIA',
  media: 'MEDIA',
  information: 'INFORMATIVA',
  info: 'INFORMATIVA',
  informativa: 'INFORMATIVA',
  not_classified: 'SIN CLASIFICAR',
  'not classified': 'SIN CLASIFICAR',
  unknown: 'SIN CLASIFICAR',
  desconocida: 'SIN CLASIFICAR',
}

function normalize(value: string) {
  return value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
}

export function mapSeverityToLabel(
  severity: string | null | undefined,
): Severity {
  if (!severity) {
    return 'SIN CLASIFICAR'
  }

  return severityLabels[normalize(severity)] ?? 'SIN CLASIFICAR'
}
