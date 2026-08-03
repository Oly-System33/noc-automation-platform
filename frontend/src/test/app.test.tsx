import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import App from '@/App'
import { AppProviders } from '@/app/providers'
import { appRoutes } from '@/app/router'
import { createQueryClient, queryClient } from '@/lib/query-client'
import { installDashboardFetchMock } from '@/test/dashboard-api-mock'

describe('aplicación', () => {
  it('renderiza la pantalla inicial dentro de los providers', async () => {
    const fetchMock = installDashboardFetchMock()
    const client = createQueryClient()

    render(
      <AppProviders client={client}>
        <App />
      </AppProviders>,
    )

    expect(
      screen.getByRole('heading', { name: 'Dashboard principal' }),
    ).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
  })

  it('navega mediante React Router', async () => {
    const user = userEvent.setup()
    const router = createMemoryRouter(appRoutes, { initialEntries: ['/'] })
    const client = createQueryClient()
    installDashboardFetchMock()

    render(
      <AppProviders client={client}>
        <RouterProvider router={router} />
      </AppProviders>,
    )

    await user.click(screen.getByRole('link', { name: 'Incidentes' }))

    expect(
      screen.getByRole('heading', { name: 'Incidentes' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Pantalla temporal.')).toBeInTheDocument()
  })

  it('inicializa el provider de TanStack Query', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <span>Query listo</span>
      </QueryClientProvider>,
    )

    expect(screen.getByText('Query listo')).toBeInTheDocument()
  })
})
