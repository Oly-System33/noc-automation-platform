import { describe, expect, it } from 'vitest'

import { compactIncidentId } from '@/features/dashboard/mappers/dashboard-data.mapper'
import {
  mapApprovalsToUi,
  mapInterventionsToUi,
  mapOperationsToUi,
} from '@/features/dashboard/mappers/dashboard-actions.mapper'
import { mapHealthQueryState } from '@/features/dashboard/mappers/dashboard-health.mapper'
import { mapSeverityToLabel } from '@/features/dashboard/mappers/dashboard-severity.mapper'
import { mapDashboardStatusToLabel } from '@/features/dashboard/mappers/dashboard-status.mapper'
import {
  formatCompactAge,
  formatCompactDuration,
  formatPollingInterval,
} from '@/features/dashboard/mappers/dashboard-time.mapper'
import {
  approvalsResponse,
  interventionsResponse,
  operationsResponse,
} from '@/test/dashboard-api-mock'

describe('mappers del dashboard', () => {
  it.each([
    ['active', 'ACTIVO'],
    ['scheduled', 'PROGRAMADO'],
    ['paused', 'PAUSADO'],
    ['executing', 'EJECUTANDO'],
    ['pending_approval', 'PEND-APP'],
    ['stuck', 'TRABADO'],
    ['failed', 'FALLIDO'],
    ['closed', 'CERRADO'],
    ['waiting_confirmation', 'ESPERA-CONF'],
    ['retry_scheduled', 'REINTENTO'],
    ['manual_required', 'MANUAL'],
    ['cancelled', 'CANCELADO'],
  ])('mapea el estado %s a %s', (status, label) => {
    expect(mapDashboardStatusToLabel(status)).toBe(label)
  })

  it('controla estados desconocidos', () => {
    expect(mapDashboardStatusToLabel('future_state')).toBe('DESCONOCIDO')
  })

  it.each([
    ['critical', 'CRÍTICA'],
    ['Disaster', 'CRÍTICA'],
    ['Crítico', 'CRÍTICA'],
    ['high', 'ALTA'],
    ['warning', 'ADVERTENCIA'],
    ['average', 'MEDIA'],
    ['medium', 'MEDIA'],
    ['information', 'INFORMATIVA'],
    ['not_classified', 'SIN CLASIFICAR'],
    ['future_severity', 'SIN CLASIFICAR'],
  ])('mapea la severidad %s a %s', (severity, label) => {
    expect(mapSeverityToLabel(severity)).toBe(label)
  })

  it('formatea segundos, minutos, horas y días', () => {
    expect(formatCompactDuration(12)).toBe('12s')
    expect(formatCompactDuration(120)).toBe('2m')
    expect(formatCompactDuration(7_200)).toBe('2h')
    expect(formatCompactDuration(172_800)).toBe('2d')
  })

  it('calcula antigüedad y controla fechas inválidas', () => {
    expect(
      formatCompactAge(
        '2026-08-03T11:58:00Z',
        '2026-08-03T12:00:00Z',
      ),
    ).toBe('2m')
    expect(formatCompactAge('fecha-invalida')).toBe('—')
    expect(formatCompactAge(null)).toBe('—')
  })

  it('formatea el intervalo de polling', () => {
    expect(formatPollingInterval(15_000)).toBe('15s')
    expect(formatPollingInterval(30_000)).toBe('30s')
    expect(formatPollingInterval(60_000)).toBe('1m')
  })

  it('compacta IDs sin perder el valor original', () => {
    expect(compactIncidentId('2024-0512')).toBe('2024-0512')
    expect(compactIncidentId('incident-very-long-identifier')).toBe(
      'inciden…fier',
    )
  })

  it('distingue salud, carga y caída de red', () => {
    expect(
      mapHealthQueryState({
        data: { status: 'ok', database: 'ok' },
        isPending: false,
        isFetching: false,
        isError: false,
      }),
    ).toEqual({ api: 'operational', database: 'operational' })
    expect(
      mapHealthQueryState({
        data: { status: 'error', database: 'unavailable' },
        isPending: false,
        isFetching: false,
        isError: false,
      }),
    ).toEqual({ api: 'unavailable', database: 'unavailable' })
    expect(
      mapHealthQueryState({
        isPending: false,
        isFetching: false,
        isError: true,
      }),
    ).toEqual({ api: 'unavailable', database: 'warning' })
  })

  it('mapea controles operativos solo para estados válidos', () => {
    const operations = mapOperationsToUi(operationsResponse)

    expect(operations[0].control).toBe('Pausar')
    expect(operations[1].control).toBe('Reanudar')
    expect(operations[0].attempts).toBe('1')
    expect(operations[0].rowId).not.toBe(operations[1].rowId)
  })

  it('mapea aprobaciones e intervenciones sin inventar datos', () => {
    const approvals = mapApprovalsToUi(approvalsResponse)
    const interventions = mapInterventionsToUi(interventionsResponse)

    expect(approvals[0]).toMatchObject({
      scheduledActionId: 51,
      objective: 'script / NOC',
      reason: 'High CPU',
    })
    expect(interventions[0]).toMatchObject({
      interventionId: 'call_flow:61',
      retrySupported: false,
      runbookAvailable: true,
    })
  })
})
