import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import App from '@/App'
import { AppProviders } from '@/app/providers'
import { appRoutes } from '@/app/router'
import { queryClient } from '@/lib/query-client'

describe('aplicación', () => {
  it('renderiza la pantalla inicial sin conectarse al backend', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    expect(screen.getByText('Frontend NOC listo')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('navega mediante React Router', async () => {
    const user = userEvent.setup()
    const router = createMemoryRouter(appRoutes, { initialEntries: ['/'] })

    render(
      <AppProviders>
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
