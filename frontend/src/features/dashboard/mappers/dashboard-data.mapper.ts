import type {
  DashboardIncident,
  DashboardIncidentListResponse,
  DashboardStatusCounts,
} from '@/features/dashboard/api/dashboard-api.types'
import { kpiDefinitions } from '@/features/dashboard/data/dashboard-visual-data'
import { mapSeverityToLabel } from '@/features/dashboard/mappers/dashboard-severity.mapper'
import { mapDashboardStatusToLabel } from '@/features/dashboard/mappers/dashboard-status.mapper'
import { formatCompactAge } from '@/features/dashboard/mappers/dashboard-time.mapper'
import type {
  Incident,
  KpiItem,
} from '@/features/dashboard/types/dashboard-ui'

const DASH = '—'

export function mapSummaryCountsToKpis(
  counts?: DashboardStatusCounts,
): KpiItem[] {
  return kpiDefinitions.map((definition) => ({
    ...definition,
    value: counts?.[definition.id] ?? null,
  }))
}

export function compactIncidentId(id: string) {
  if (id.length <= 12) {
    return id
  }

  return `${id.slice(0, 7)}…${id.slice(-4)}`
}

export function mapIncidentToUi(
  incident: DashboardIncident,
  generatedAt: string,
): Incident {
  return {
    id: compactIncidentId(incident.event_id),
    fullId: incident.event_id,
    client: incident.client?.trim() || DASH,
    host: incident.host?.trim() || DASH,
    trigger: incident.trigger?.trim() || DASH,
    severity: mapSeverityToLabel(incident.severity),
    status: mapDashboardStatusToLabel(incident.display_status),
    action: incident.current_action?.trim() || null,
    time: formatCompactAge(incident.opened_at, generatedAt),
  }
}

export function mapIncidentListToUi(
  response?: DashboardIncidentListResponse,
): Incident[] {
  if (!response) {
    return []
  }

  return response.items.map((incident) =>
    mapIncidentToUi(incident, response.generated_at),
  )
}
