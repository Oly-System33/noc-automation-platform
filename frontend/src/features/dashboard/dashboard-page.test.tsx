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
  it('organiza los cuatro paneles en la cuadrícula responsive definitiva', () => {
    renderDashboard()

    const grid = screen.getByTestId('dashboard-content-grid')
    const panelHeadings = within(grid).getAllByRole('heading', { level: 2 })

    expect(grid).toHaveClass(
      'dashboard-content-grid',
      'grid',
      'min-h-0',
      'flex-1',
      'grid-cols-1',
      'min-[1100px]:grid-cols-2',
      'min-[1100px]:grid-rows-[minmax(320px,1.38fr)_minmax(220px,1fr)]',
    )
    expect(panelHeadings.map((heading) => heading.textContent)).toEqual([
      'Incidentes recientes',
      'Operaciones activas',
      'Requiere intervención manual',
      'Aprobaciones pendientes',
    ])

    for (const heading of panelHeadings) {
      expect(heading.closest('[data-slot="card"]')).toHaveClass(
        'h-full',
        'min-h-0',
      )
    }

    for (const table of within(grid).getAllByRole('table')) {
      expect(table.parentElement).toHaveClass(
        'min-h-0',
        'flex-1',
        'overflow-auto',
      )
    }
  })

  it('conserva el orden y las consultas al simular un ancho reducido', async () => {
    const originalWidth = window.innerWidth
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 960,
    })

    try {
      const { fetchMock } = renderDashboard()
      const grid = screen.getByTestId('dashboard-content-grid')

      await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6))
      window.dispatchEvent(new Event('resize'))

      expect(grid).toHaveClass('grid-cols-1', 'min-[1100px]:grid-cols-2')
      expect(within(grid).getAllByRole('table')).toHaveLength(4)
      expect(fetchMock).toHaveBeenCalledTimes(6)
    } finally {
      Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        value: originalWidth,
      })
    }
  })

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

  it('renderiza operaciones, aprobaciones e intervenciones reales', async () => {
    renderDashboard()

    expect(screen.getByText('Operaciones activas')).toBeInTheDocument()
    expect(screen.getByText('Aprobaciones pendientes')).toBeInTheDocument()
    expect(screen.getByText('Requiere intervención manual')).toBeInTheDocument()
    expect(await screen.findByLabelText('1 elementos')).toHaveTextContent('1')
    expect(within(screen.getByRole('table', { name: 'Operaciones activas' })).getByText('jira')).toBeInTheDocument()
    expect(screen.getByText('script / NOC')).toBeInTheDocument()
    expect(screen.getByText('Confirmación manual requerida')).toBeInTheDocument()
    expect(screen.getAllByText('Ver runbook')).toHaveLength(1)
    expect(screen.getAllByText('Reintentar flujo')).toHaveLength(1)
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

  it('pausa y aprueba mediante los endpoints reales', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderDashboard({ health: healthResponse })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6))

    const pauseButton = await screen.findByRole('button', { name: /^Pausar/ })
    const approveButton = await screen.findByRole('button', { name: /^Aprobar/ })
    await user.click(pauseButton)
    await user.click(approveButton)

    await waitFor(() => {
      const calls = fetchMock.mock.calls.map(([url, init]) => ({ url: String(url), method: init?.method }))
      expect(calls).toContainEqual(expect.objectContaining({ url: expect.stringContaining('/api/scheduled-actions/41/pause'), method: 'POST' }))
      expect(calls).toContainEqual(expect.objectContaining({ url: expect.stringContaining('/api/scheduled-actions/51/approve'), method: 'POST' }))
    })
  })

  it('consulta runbook solo al abrir y controla retry no seguro', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderDashboard()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6))
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/runbook'))).toBe(false)

    await user.click(await screen.findByRole('button', { name: 'Ver runbook' }))
    expect(await screen.findByText('Runbook asociado')).toBeInTheDocument()
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/runbook'))).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Cerrar runbook' }))

    await user.click(screen.getByRole('button', { name: /Reintento no seguro/ }))
    expect(screen.getByRole('status')).toHaveTextContent('El reintento no es seguro')
    expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/retry') && init?.method === 'POST')).toBe(false)
  })

  it('refresca las seis consultas principales manualmente', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderDashboard()
    const refreshButton = screen.getByRole('button', {
      name: 'Actualizar dashboard',
    })

    await waitFor(() => expect(refreshButton).toBeEnabled())
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6))
    await user.click(refreshButton)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(12))

    const paths = fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)
    expect(paths.filter((path) => path === '/health')).toHaveLength(2)
    expect(
      paths.filter((path) => path === '/api/dashboard/summary'),
    ).toHaveLength(2)
    expect(paths.filter((path) => path === '/api/incidents')).toHaveLength(2)
    expect(paths.filter((path) => path === '/api/operations')).toHaveLength(2)
    expect(paths.filter((path) => path === '/api/approvals')).toHaveLength(2)
    expect(paths.filter((path) => path === '/api/interventions')).toHaveLength(2)
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
