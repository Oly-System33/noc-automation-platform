import {
  Activity,
  Bell,
  CalendarDays,
  CheckCircle,
  ClipboardList,
  GitBranch,
  LayoutDashboard,
  Link,
  Pause,
  Play,
  Settings,
  ShieldCheck,
  User,
  XCircle,
} from 'lucide-react'

import type {
  KpiDefinition,
  NavigationItem,
} from '@/features/dashboard/types/dashboard-ui'

// Visual-only metadata. Trend lines remain decorative until trend data exists.
export const kpiDefinitions: KpiDefinition[] = [
  {
    id: 'active',
    label: 'Activas',
    tone: 'cyan',
    icon: Activity,
    trendPath:
      'M2 16 L12 15 L20 16 L28 13 L37 14 L45 11 L54 13 L62 7 L72 10 L81 8 L90 9',
  },
  {
    id: 'scheduled',
    label: 'Programadas',
    tone: 'teal',
    icon: CalendarDays,
    trendPath:
      'M2 15 L12 16 L20 13 L28 14 L37 10 L45 13 L54 8 L62 12 L72 7 L81 11 L90 8',
  },
  {
    id: 'paused',
    label: 'Pausadas',
    tone: 'purple',
    icon: Pause,
    trendPath:
      'M2 16 L12 15 L20 16 L28 12 L37 14 L45 9 L54 13 L62 10 L72 13 L81 11 L90 7',
  },
  {
    id: 'executing',
    label: 'Ejecutando',
    tone: 'green',
    icon: Play,
    trendPath:
      'M2 16 L12 15 L20 16 L28 14 L37 13 L45 6 L54 9 L62 10 L72 9 L81 8 L90 5',
  },
  {
    id: 'pending_approval',
    label: 'Pend. aprobación',
    tone: 'yellow',
    icon: User,
    trendPath:
      'M2 16 L12 14 L20 15 L28 11 L37 13 L45 9 L54 12 L62 6 L72 10 L81 11 L90 7',
  },
  {
    id: 'stuck',
    label: 'Trabadas',
    tone: 'orange',
    icon: Link,
    trendPath:
      'M2 16 L12 15 L20 12 L28 14 L37 8 L45 12 L54 9 L62 6 L72 11 L81 8 L90 9',
  },
  {
    id: 'failed',
    label: 'Fallidas',
    tone: 'red',
    icon: XCircle,
    trendPath:
      'M2 16 L12 16 L20 13 L28 15 L37 9 L45 12 L54 6 L62 11 L72 8 L81 11 L90 5',
  },
  {
    id: 'closed',
    label: 'Cerradas',
    tone: 'slate',
    icon: CheckCircle,
    trendPath:
      'M2 16 L12 14 L20 15 L28 12 L37 13 L45 8 L54 12 L62 9 L72 11 L81 8 L90 9',
  },
]

export const navigationItems: NavigationItem[] = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Incidentes', path: '/incidentes', icon: Bell },
  { label: 'Operaciones', path: '/operaciones', icon: GitBranch },
  { label: 'Aprobaciones', path: '/aprobaciones', icon: ShieldCheck },
  { label: 'Auditoría', path: '/auditoria', icon: ClipboardList },
  { label: 'Configuración', path: '/configuracion', icon: Settings },
]
