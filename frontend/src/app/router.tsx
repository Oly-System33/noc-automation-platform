import { createBrowserRouter, type RouteObject } from 'react-router-dom'

import { HomePage } from '@/pages/home-page'
import { AppLayout } from '@/components/layout/app-layout'
import { ApprovalsPage } from '@/pages/approvals-page'
import { AuditPage } from '@/pages/audit-page'
import { ConfigurationPage } from '@/pages/configuration-page'
import { IncidentDetailPage } from '@/pages/incident-detail-page'
import { IncidentsPage } from '@/pages/incidents-page'
import { OperationsPage } from '@/pages/operations-page'

export const appRoutes: RouteObject[] = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'incidentes', element: <IncidentsPage /> },
      { path: 'incidentes/:eventId', element: <IncidentDetailPage /> },
      { path: 'operaciones', element: <OperationsPage /> },
      { path: 'aprobaciones', element: <ApprovalsPage /> },
      { path: 'auditoria', element: <AuditPage /> },
      { path: 'configuracion', element: <ConfigurationPage /> },
    ],
  },
]

export const router = createBrowserRouter(appRoutes)
