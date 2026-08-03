import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { AppProviders } from '@/app/providers'
import { appRoutes } from '@/app/router'
import { dashboardQueryKeys } from '@/features/dashboard/api/dashboard-query-keys'
import { createQueryClient } from '@/lib/query-client'
import {
  healthResponse,
  installDashboardFetchMock,
} from '@/test/dashboard-api-mock'

type FetchOptions = Parameters<typeof installDashboardFetchMock>[0]

function renderDashboard(options?: FetchOptions) {
  const fetchMock = installDashboardFetchMock(options)
  const client = createQueryClient()
  client.setQueryDefaults(dashboardQueryKeys.all, { retry: false })
  const router = createMemoryRouter(appRoutes, { initialEntries: ['/'] })

  render(
    <AppProviders client={client}>
      <RouterProvider router={router} />
    </AppProviders>,
  )

  return { client, fetchMock, router }
}

describe('Dashboard principal integrado', () => {
  it('renderiza los ocho KPI recibidos y conserva su estructura uniforme', async () => {
    renderDashboard()

    expect(
      screen.getByRole('heading', { name: 'Dashboard principal' }),
    ).toBeInTheDocument()
    expect(await screen.findByLabelText('Activas: 12')).toBeInTheDocument()
    expect(screen.getByLabelText('Programadas: 6')).toBeInTheDocument()
    expect(screen.getByLabelText('Pausadas: 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Ejecutando: 4')).toBeInTheDocument()
    expect(screen.getByLabelText('Pend. aprobación: 2')).toBeInTheDocument()
    expect(screen.getByLabelText('Trabadas: 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Fallidas: 2')).toBeInTheDocument()
    expect(screen.getByLabelText('Cerradas: 28')).toBeInTheDocument()

    const cards = screen.getAllByTestId('kpi-card')
    expect(cards).toHaveLength(8)
    expect(new Set(cards.map((card) => card.className)).size).toBe(1)
    expect(cards.every((card) => card.dataset.size === 'uniform')).toBe(true)
  })

  it('renderiza seis incidentes reales mapeados', async () => {
    renderDashboard()

    const table = screen.getByRole('table', { name: 'Incidentes recientes' })
    expect(await within(table).findByText('CRÍTICA')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(7)
    expect(within(table).getAllByText('ALTA')).not.toHaveLength(0)
    expect(within(table).getByText('ADVERTENCIA')).toBeInTheDocument()
    expect(within(table).getByText('MEDIA')).toBeInTheDocument()
    expect(within(table).getByText('INFORMATIVA')).toBeInTheDocument()
    expect(within(table).getByText('PEND-APP')).toBeInTheDocument()
    expect(within(table).getByText('jira, telegram')).toBeInTheDocument()
    expect(within(table).getByText('—')).toBeInTheDocument()
  })

  it('mantiene operaciones, aprobaciones e intervención manual estáticas', () => {
    renderDashboard()

    expect(screen.getByText('Operaciones activas')).toBeInTheDocument()
    expect(screen.getByText('Aprobaciones pendientes')).toBeInTheDocument()
    expect(screen.getByText('Requiere intervención manual')).toBeInTheDocument()
    expect(screen.getByLabelText('3 elementos')).toHaveTextContent('3')
    expect(screen.getAllByText('Ver runbook')).toHaveLength(3)
    expect(screen.getAllByText('Reintentar flujo')).toHaveLength(3)
    expect(screen.queryByText('Abrir Jira')).not.toBeInTheDocument()
  })

  it('usa el logo, la navegación y salud real accesible', async () => {
    renderDashboard()

    expect(screen.getByRole('img', { name: 'Logo NOC' })).toBeInTheDocument()
    expect(
      screen.getByRole('navigation', { name: 'Navegación principal' }),
    ).toBeInTheDocument()
    expect(await screen.findByLabelText('FastAPI: operativo')).toBeInTheDocument()
    expect(screen.getByLabelText('DB: operativa')).toBeInTheDocument()
    expect(screen.getAllByRole('table')).toHaveLength(4)
  })

  it('muestra FastAPI y PostgreSQL no disponibles con el 503 real', async () => {
    renderDashboard({
      health: { status: 'error', database: 'unavailable' },
    })

    expect(
      await screen.findByLabelText('FastAPI: no disponible'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('DB: no disponible')).toBeInTheDocument()
  })

  it('los botones estáticos no generan requests adicionales', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderDashboard({ health: healthResponse })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))

    await user.click(screen.getAllByRole('button', { name: /^Pausar/ })[0])
    await user.click(screen.getAllByRole('button', { name: /^Aprobar/ })[0])
    await user.click(screen.getAllByRole('button', { name: /^Ver runbook/ })[0])
    await user.click(
      screen.getAllByRole('button', { name: /^Reintentar flujo/ })[0],
    )

    expect(fetchMock).toHaveBeenCalledTimes(3)
    const urls = fetchMock.mock.calls.map(([url]) => String(url))
    expect(urls.some((url) => url.includes('/api/operations'))).toBe(false)
    expect(urls.some((url) => url.includes('/api/approvals'))).toBe(false)
  })

  it('refresca health, summary e incidentes manualmente', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderDashboard()
    const refreshButton = screen.getByRole('button', {
      name: 'Actualizar dashboard',
    })

    await waitFor(() => expect(refreshButton).toBeEnabled())
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    await user.click(refreshButton)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6))

    const paths = fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)
    expect(paths.filter((path) => path === '/health')).toHaveLength(2)
    expect(
      paths.filter((path) => path === '/api/dashboard/summary'),
    ).toHaveLength(2)
    expect(paths.filter((path) => path === '/api/incidents')).toHaveLength(2)
  })

  it('mantiene la navegación básica hacia los placeholders', async () => {
    const user = userEvent.setup()
    renderDashboard()

    await user.click(screen.getByRole('link', { name: 'Incidentes' }))

    expect(
      screen.getByRole('heading', { name: 'Incidentes' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Pantalla temporal.')).toBeInTheDocument()
  })
})
