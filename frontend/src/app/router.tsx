import { createBrowserRouter, type RouteObject } from 'react-router-dom'

import { HomePage } from '@/pages/home-page'
import { PlaceholderPage } from '@/pages/placeholder-page'

export const appRoutes: RouteObject[] = [
  {
    path: '/',
    element: <HomePage />,
  },
  {
    path: '/incidentes',
    element: <PlaceholderPage title="Incidentes" />,
  },
  {
    path: '/operaciones',
    element: <PlaceholderPage title="Operaciones" />,
  },
  {
    path: '/aprobaciones',
    element: <PlaceholderPage title="Aprobaciones" />,
  },
  {
    path: '/auditoria',
    element: <PlaceholderPage title="Auditoría" />,
  },
  {
    path: '/configuracion',
    element: <PlaceholderPage title="Configuración" />,
  },
]

export const router = createBrowserRouter(appRoutes)
