import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AppProviders } from '@/app/providers'
import { appRoutes } from '@/app/router'

function renderDashboard() {
  const router = createMemoryRouter(appRoutes, { initialEntries: ['/'] })

  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  )

  return router
}

describe('Dashboard principal estático', () => {
  it('renderiza el dashboard y sus ocho KPI uniformes', () => {
    renderDashboard()

    expect(
      screen.getByRole('heading', { name: 'Dashboard principal' }),
    ).toBeInTheDocument()

    const cards = screen.getAllByTestId('kpi-card')
    expect(cards).toHaveLength(8)
    expect(new Set(cards.map((card) => card.className)).size).toBe(1)
    expect(cards.every((card) => card.dataset.size === 'uniform')).toBe(true)
    expect(screen.getByText('Pend. aprobación')).toBeInTheDocument()
    expect(screen.getByText('Cerradas')).toBeInTheDocument()
  })

  it('renderiza seis incidentes con severidades y estados visibles', () => {
    renderDashboard()

    expect(screen.getByText('Incidentes recientes')).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Incidentes recientes' })
    expect(within(table).getAllByRole('row')).toHaveLength(7)
    expect(within(table).getAllByText('CRÍTICA')).not.toHaveLength(0)
    expect(within(table).getAllByText('ALTA')).not.toHaveLength(0)
    expect(within(table).getByText('ADVERTENCIA')).toBeInTheDocument()
    expect(within(table).getAllByText('MEDIA')).not.toHaveLength(0)
    expect(within(table).getByText('PEND-APP')).toBeInTheDocument()
  })

  it('renderiza operaciones y aprobaciones pendientes', () => {
    renderDashboard()

    expect(screen.getByText('Operaciones activas')).toBeInTheDocument()
    expect(screen.getByText('Aprobaciones pendientes')).toBeInTheDocument()
    expect(
      screen.getByRole('table', { name: 'Operaciones activas' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('table', { name: 'Aprobaciones pendientes' }),
    ).toBeInTheDocument()
  })

  it('renderiza la intervención manual y solamente sus acciones aprobadas', () => {
    renderDashboard()

    expect(screen.getByText('Requiere intervención manual')).toBeInTheDocument()
    expect(screen.getByLabelText('3 elementos')).toHaveTextContent('3')
    expect(screen.getAllByText('Ver runbook')).toHaveLength(3)
    expect(screen.getAllByText('Reintentar flujo')).toHaveLength(3)
    expect(screen.queryByText('Abrir Jira')).not.toBeInTheDocument()
  })

  it('usa el logo definitivo y navegación accesible', () => {
    renderDashboard()

    expect(screen.getByRole('img', { name: 'Logo NOC' })).toBeInTheDocument()
    expect(
      screen.getByRole('navigation', { name: 'Navegación principal' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getAllByRole('table')).toHaveLength(4)
  })

  it('no realiza llamadas HTTP al cargar ni al usar botones estáticos', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    renderDashboard()

    await user.click(screen.getAllByRole('button', { name: /^Pausar/ })[0])
    await user.click(screen.getAllByRole('button', { name: /^Aprobar/ })[0])
    await user.click(screen.getAllByRole('button', { name: /^Ver runbook/ })[0])
    await user.click(
      screen.getAllByRole('button', { name: /^Reintentar flujo/ })[0],
    )

    expect(fetchMock).not.toHaveBeenCalled()
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
