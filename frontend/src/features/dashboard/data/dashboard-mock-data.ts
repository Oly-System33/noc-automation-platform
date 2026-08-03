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
  Approval,
  Incident,
  KpiItem,
  ManualIntervention,
  NavigationItem,
  Operation,
} from '@/features/dashboard/types/dashboard-ui'

// Temporary static UI data for F2. Replaced by API data in a later phase.
export const kpiItems: KpiItem[] = [
  {
    id: 'active',
    label: 'Activas',
    value: 12,
    tone: 'cyan',
    icon: Activity,
    trendPath: 'M2 16 L12 15 L20 16 L28 13 L37 14 L45 11 L54 13 L62 7 L72 10 L81 8 L90 9',
  },
  {
    id: 'scheduled',
    label: 'Programadas',
    value: 6,
    tone: 'teal',
    icon: CalendarDays,
    trendPath: 'M2 15 L12 16 L20 13 L28 14 L37 10 L45 13 L54 8 L62 12 L72 7 L81 11 L90 8',
  },
  {
    id: 'paused',
    label: 'Pausadas',
    value: 3,
    tone: 'purple',
    icon: Pause,
    trendPath: 'M2 16 L12 15 L20 16 L28 12 L37 14 L45 9 L54 13 L62 10 L72 13 L81 11 L90 7',
  },
  {
    id: 'running',
    label: 'Ejecutando',
    value: 4,
    tone: 'green',
    icon: Play,
    trendPath: 'M2 16 L12 15 L20 16 L28 14 L37 13 L45 6 L54 9 L62 10 L72 9 L81 8 L90 5',
  },
  {
    id: 'approval',
    label: 'Pend. aprobación',
    value: 2,
    tone: 'yellow',
    icon: User,
    trendPath: 'M2 16 L12 14 L20 15 L28 11 L37 13 L45 9 L54 12 L62 6 L72 10 L81 11 L90 7',
  },
  {
    id: 'blocked',
    label: 'Trabadas',
    value: 1,
    tone: 'orange',
    icon: Link,
    trendPath: 'M2 16 L12 15 L20 12 L28 14 L37 8 L45 12 L54 9 L62 6 L72 11 L81 8 L90 9',
  },
  {
    id: 'failed',
    label: 'Fallidas',
    value: 2,
    tone: 'red',
    icon: XCircle,
    trendPath: 'M2 16 L12 16 L20 13 L28 15 L37 9 L45 12 L54 6 L62 11 L72 8 L81 11 L90 5',
  },
  {
    id: 'closed',
    label: 'Cerradas',
    value: 28,
    tone: 'slate',
    icon: CheckCircle,
    trendPath: 'M2 16 L12 14 L20 15 L28 12 L37 13 L45 8 L54 12 L62 9 L72 11 L81 8 L90 9',
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

export const incidents: Incident[] = [
  { id: '2024-0512', client: 'Banco X', host: 'srv-core-01', trigger: 'Zabbix agent unreachable', severity: 'CRÍTICA', status: 'ACTIVO', action: 'jira', time: '2m' },
  { id: '2024-0511', client: 'Banco Demo', host: 'db-prod-02', trigger: 'High CPU', severity: 'ALTA', status: 'EJECUTANDO', action: 'calls', time: '4m' },
  { id: '2024-0510', client: 'Banco X', host: 'app-web-03', trigger: 'Disk space low', severity: 'ADVERTENCIA', status: 'PROGRAMADO', action: 'telegram', time: '12m' },
  { id: '2024-0509', client: 'Banco Demo', host: 'net-fw-01', trigger: 'Interface down', severity: 'MEDIA', status: 'PAUSADO', action: 'email', time: '18m' },
  { id: '2024-0508', client: 'Banco X', host: 'db-replica-01', trigger: 'Replication lag high', severity: 'ALTA', status: 'PEND-APP', action: 'jira', time: '27m' },
  { id: '2024-0507', client: 'Banco Demo', host: 'vm-app-07', trigger: 'Service not responding', severity: 'MEDIA', status: 'TRABADO', action: 'calls', time: '37m' },
]

export const operations: Operation[] = [
  { action: 'jira', client: 'Banco X', status: 'EJECUTANDO', target: 'Jira API', attempts: '1/3', control: 'Pausar' },
  { action: 'calls', client: 'Banco Demo', status: 'EJECUTANDO', target: 'Guardia NOC', attempts: '1/3', control: 'Pausar' },
  { action: 'telegram', client: 'Banco X', status: 'PROGRAMADO', target: '#noc-alertas', attempts: '0/3', control: 'Pausar' },
  { action: 'email', client: 'Banco Demo', status: 'PAUSADO', target: 'Canal NOC', attempts: '0/3', control: 'Reanudar' },
  { action: 'script', client: 'Banco X', status: 'EJECUTANDO', target: 'vm-app-07', attempts: '2/5', control: 'Pausar' },
]

export const approvals: Approval[] = [
  { id: '2024-0021', client: 'Banco X', objective: 'Reiniciar servicio srv-core-01 (Nginx)', reason: 'Servicio sin respuesta por >5 min', time: '3m' },
  { id: '2024-0022', client: 'Banco Demo', objective: 'Ejecutar job de maintenance', reason: 'Mantenimiento programado', time: '8m' },
  { id: '2024-0023', client: 'Banco X', objective: 'Cambiar perfil de QoS en core-01', reason: 'Sistemas', time: '12m' },
]

export const manualInterventions: ManualIntervention[] = [
  { id: '2024-0091', client: 'Banco Demo', description: 'Fallo de autenticación en DB primaria', severity: 'CRÍTICA', time: '18m' },
  { id: '2024-0090', client: 'Banco X', description: 'Backups fallando en 2 nodos', severity: 'ALTA', time: '25m' },
  { id: '2024-0089', client: 'Banco Demo', description: 'Consumo de memoria > 90% en app-web-03', severity: 'ALTA', time: '37m' },
]
