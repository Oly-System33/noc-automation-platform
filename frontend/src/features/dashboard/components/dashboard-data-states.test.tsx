import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DashboardHeader } from '@/features/dashboard/components/dashboard-header'
import { IncidentsTable } from '@/features/dashboard/components/incidents-table'
import { KpiGrid } from '@/features/dashboard/components/kpi-grid'
import type { Incident } from '@/features/dashboard/types/dashboard-ui'
import { summaryResponse } from '@/test/dashboard-api-mock'

const unknownIncident: Incident = {
  id: 'event-1',
  fullId: 'event-1',
  client: '—',
  host: '—',
  trigger: '—',
  severity: 'SIN CLASIFICAR',
  status: 'DESCONOCIDO',
  action: null,
  time: '—',
}

describe('estados de datos del dashboard', () => {
  it('mantiene ocho KPI con placeholders durante la carga', () => {
    render(
      <KpiGrid
        isLoading
        isError={false}
        isRetrying={false}
        onRetry={() => undefined}
      />,
    )

    expect(screen.getAllByTestId('kpi-card')).toHaveLength(8)
    expect(screen.getAllByLabelText(/^Cargando /)).toHaveLength(8)
  })

  it('no usa valores mock ante error y permite reintentar KPI', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(
      <KpiGrid
        isLoading={false}
        isError
        isRetrying={false}
        onRetry={onRetry}
      />,
    )

    expect(screen.getByLabelText('Activas: sin datos')).toHaveTextContent('—')
    expect(
      screen.getByText('No fue posible cargar los indicadores'),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('conserva KPI previos e informa un refetch fallido', () => {
    render(
      <KpiGrid
        counts={summaryResponse.counts}
        isLoading={false}
        isError
        isRetrying={false}
        onRetry={() => undefined}
      />,
    )

    expect(screen.getByLabelText('Activas: 12')).toBeInTheDocument()
    expect(
      screen.getByText('No fue posible actualizar los indicadores'),
    ).toBeInTheDocument()
  })

  it('renderiza seis filas skeleton para incidentes', () => {
    render(
      <IncidentsTable
        incidents={[]}
        hasResponse={false}
        isLoading
        isError={false}
        isFetching
        onRetry={() => undefined}
      />,
    )

    expect(screen.getAllByTestId('incident-skeleton')).toHaveLength(6)
  })

  it('muestra lista vacía sin datos mock', () => {
    render(
      <IncidentsTable
        incidents={[]}
        hasResponse
        isLoading={false}
        isError={false}
        isFetching={false}
        onRetry={() => undefined}
      />,
    )

    expect(screen.getByText('No hay incidentes recientes')).toBeInTheDocument()
  })

  it('muestra error controlado y vuelve a consultar', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(
      <IncidentsTable
        incidents={[]}
        hasResponse={false}
        isLoading={false}
        isError
        isFetching={false}
        onRetry={onRetry}
      />,
    )

    expect(
      screen.getByText('No fue posible cargar los incidentes'),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('renderiza estado y severidad desconocidos sin romperse', () => {
    render(
      <IncidentsTable
        incidents={[unknownIncident]}
        hasResponse
        isLoading={false}
        isError={false}
        isFetching={false}
        onRetry={() => undefined}
      />,
    )

    expect(screen.getByText('DESCONOCIDO')).toBeInTheDocument()
    expect(screen.getByText('SIN CLASIFICAR')).toBeInTheDocument()
  })

  it('conserva incidentes previos e informa un refetch fallido', () => {
    render(
      <IncidentsTable
        incidents={[unknownIncident]}
        hasResponse
        isLoading={false}
        isError
        isFetching={false}
        onRetry={() => undefined}
      />,
    )

    expect(screen.getByText('DESCONOCIDO')).toBeInTheDocument()
    expect(screen.getByLabelText('Actualización fallida')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('mantiene estados accesibles y etiquetas dinámicas en el header', () => {
    render(
      <DashboardHeader
        apiState="unavailable"
        databaseState="warning"
        pollingLabel="30s"
        lastUpdatedLabel="12s"
        isRefreshing={false}
        onRefresh={() => undefined}
      />,
    )

    expect(screen.getByLabelText('FastAPI: no disponible')).toBeInTheDocument()
    expect(screen.getByLabelText('DB: advertencia')).toBeInTheDocument()
    expect(screen.getByText('30s')).toBeInTheDocument()
    expect(screen.getByText('12s')).toBeInTheDocument()
  })
})
