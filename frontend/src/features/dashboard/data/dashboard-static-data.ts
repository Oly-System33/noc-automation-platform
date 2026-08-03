import type {
  Approval,
  ManualIntervention,
  Operation,
} from '@/features/dashboard/types/dashboard-ui'

// Temporary static F2 data. Replaced by API data in later integration phases.
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
