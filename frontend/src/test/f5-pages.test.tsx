import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { AppProviders } from '@/app/providers'
import { appRoutes } from '@/app/router'
import { createQueryClient } from '@/lib/query-client'
import { approvalsResponse, incidentsResponse, installDashboardFetchMock } from '@/test/dashboard-api-mock'

function renderRoute(path: string, options?: Parameters<typeof installDashboardFetchMock>[0]) {
  const fetchMock = installDashboardFetchMock(options)
  const client = createQueryClient()
  client.setQueryDefaults(['dashboard'], { retry: false })
  const router = createMemoryRouter(appRoutes, { initialEntries: [path] })
  render(<AppProviders client={client}><RouterProvider router={router} /></AppProviders>)
  return { fetchMock, router }
}

describe('pantallas F5', () => {
  it.each([
    ['/incidentes', 'Incidentes'],
    ['/operaciones', 'Operaciones'],
    ['/aprobaciones', 'Aprobaciones'],
    ['/auditoria', 'Auditoría'],
    ['/configuracion', 'Configuración'],
  ])('renderiza %s y mantiene activa su entrada de sidebar', async (path, title) => {
    renderRoute(path)

    expect(await screen.findByRole('heading', { name: title, level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: title })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('mantiene la ruta de incidentes activa en el detalle y muestra secciones seguras', async () => {
    renderRoute('/incidentes/event-0512')
    expect(await screen.findByRole('heading', { name: 'Incidente event-0512' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Incidentes' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { name: 'Operaciones' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Acciones' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Intentos' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Aprobaciones' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Intervenciones' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Auditoría' })).toBeInTheDocument()
    expect(screen.getAllByText('jira')).toHaveLength(2)
  })

  it('convierte todas las acciones del dashboard en enlaces reales', async () => {
    renderRoute('/')
    const links = await screen.findAllByRole('link', { name: 'Ver todas' })
    expect(links.map((link) => link.getAttribute('href'))).toEqual(['/incidentes', '/operaciones', '/operaciones?view=interventions', '/aprobaciones?status=pending'])
    expect(screen.getByRole('link', { name: 'Ver historial de operaciones' })).toHaveAttribute('href', '/operaciones')
    expect(screen.getByRole('link', { name: 'Ver todas las intervenciones' })).toHaveAttribute('href', '/operaciones?view=interventions')
  })

  it('envía filtros explícitos y pagina mediante offset de backend', async () => {
    const user = userEvent.setup()
    const response = { ...incidentsResponse, total: 25, limit: 20 }
    const { fetchMock } = renderRoute('/incidentes', { incidents: response })
    await screen.findByRole('table', { name: 'Incidentes' })
    await user.type(screen.getByLabelText('Buscar'), 'cpu')
    await user.type(screen.getByLabelText('Cliente'), 'Banco X')
    await user.click(screen.getByRole('button', { name: 'Buscar' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => { const url = new URL(String(input)); return url.pathname === '/api/incidents' && url.searchParams.get('search') === 'cpu' && url.searchParams.get('client') === 'Banco X' && !url.searchParams.has('severity') })).toBe(true))
    await user.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => new URL(String(input)).searchParams.get('offset') === '20')).toBe(true))
  })

  it('respeta capacidades de intervención y no solicita retry bloqueado', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderRoute('/operaciones?view=interventions')
    const retry = await screen.findByRole('button', { name: 'Reintentar' })
    expect(retry).toBeDisabled()
    expect(retry).toHaveAttribute('title', 'retry_not_safe')
    expect(screen.getByRole('button', { name: 'Runbook' })).toBeEnabled()
    await user.click(retry)
    expect(fetchMock.mock.calls.some(([input, init]) => String(input).endsWith('/retry') && init?.method === 'POST')).toBe(false)
  })

  it('presenta el historial de aprobaciones como solo lectura', async () => {
    const approved = { ...approvalsResponse, items: [{ ...approvalsResponse.items[0], decision: 'approved' as const, result: 'executed', decided_at: '2026-08-03T12:00:00Z' }] }
    renderRoute('/aprobaciones?status=approved', { approvals: approved })
    const table = await screen.findByRole('table', { name: 'Aprobaciones' })
    expect(await within(table).findByText('Solo lectura: executed')).toBeInTheDocument()
    expect(within(table).queryByRole('button', { name: 'Aprobar' })).not.toBeInTheDocument()
  })

  it('mantiene pausa, reanudación y aprobación en las páginas completas', async () => {
    const user = userEvent.setup()
    const { fetchMock } = renderRoute('/operaciones')
    const operations = await screen.findByRole('table', { name: 'Operaciones' })

    const pause = await within(operations).findByRole('button', { name: 'Pausar' })
    const resume = within(operations).getByRole('button', { name: 'Reanudar' })
    await user.click(pause)
    await user.click(resume)
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([input, init]) =>
        String(input).endsWith('/pause') && init?.method === 'POST',
      )).toBe(true)
      expect(fetchMock.mock.calls.some(([input, init]) =>
        String(input).endsWith('/resume') && init?.method === 'POST',
      )).toBe(true)
    })

    await user.click(screen.getByRole('link', { name: 'Aprobaciones' }))
    const approvals = await screen.findByRole('table', { name: 'Aprobaciones' })
    await user.click(within(approvals).getByRole('button', { name: 'Aprobar' }))
    expect(fetchMock.mock.calls.some(([input, init]) =>
      String(input).endsWith('/approve') && init?.method === 'POST',
    )).toBe(true)
  })

  it('muestra estados vacío y error con reintento sin datos mock', async () => {
    const user = userEvent.setup()
    const empty = { ...incidentsResponse, items: [], total: 0 }
    const emptyRender = renderRoute('/incidentes', { incidents: empty })
    expect(await screen.findByText('No hay incidentes para estos filtros')).toBeInTheDocument()
    emptyRender.router.dispose()
    cleanup()

    renderRoute('/auditoria', { failingPaths: ['/api/audit-logs'] })
    expect(await screen.findByText('No fue posible cargar los datos.')).toBeInTheDocument()
    const retry = screen.getByRole('button', { name: 'Reintentar' })
    await user.click(retry)
    expect(retry).toBeInTheDocument()
  })

  it('no renderiza contexto de auditoría ni valores no permitidos de configuración', async () => {
    const user = userEvent.setup()
    renderRoute('/auditoria')
    expect(await screen.findByText('Contexto disponible')).toBeInTheDocument()
    expect(screen.queryByText('audit-secret-value')).not.toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Configuración' }))
    expect(await screen.findByText('Cantidad de runbooks')).toBeInTheDocument()
    expect(screen.queryByText('configuration-secret-value')).not.toBeInTheDocument()
  })
})
