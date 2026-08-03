import { cn } from '@/lib/utils'
import type { VisibleStatus } from '@/features/dashboard/types/dashboard-ui'

const statusClasses: Record<VisibleStatus, string> = {
  ACTIVO: 'border-blue/80 bg-blue/10 text-blue',
  EJECUTANDO: 'border-green/80 bg-green/10 text-green',
  PROGRAMADO: 'border-cyan/70 bg-cyan/10 text-cyan',
  PAUSADO: 'border-purple/80 bg-purple/10 text-primary-hover',
  'PEND-APP': 'border-yellow/80 bg-yellow/10 text-yellow',
  TRABADO: 'border-red/80 bg-red/10 text-red',
  FALLIDO: 'border-red/80 bg-red/10 text-red',
  CERRADO: 'border-text-muted/70 bg-text-muted/10 text-text-secondary',
  'ESPERA-CONF': 'border-yellow/80 bg-yellow/10 text-yellow',
  REINTENTO: 'border-orange/80 bg-orange/10 text-orange',
  MANUAL: 'border-purple/80 bg-purple/10 text-primary-hover',
  CANCELADO: 'border-text-muted/70 bg-text-muted/10 text-text-muted',
  DESCONOCIDO: 'border-text-muted/70 bg-text-muted/10 text-text-muted',
}

export function StatusBadge({ status }: { status: VisibleStatus }) {
  return (
    <span
      className={cn(
        'inline-flex h-5 w-[78px] items-center justify-center rounded-[3px] border text-[8px] leading-none font-medium',
        statusClasses[status],
      )}
    >
      {status}
    </span>
  )
}
