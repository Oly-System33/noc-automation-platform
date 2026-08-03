import { cn } from '@/lib/utils'
import type { Severity } from '@/features/dashboard/types/dashboard-ui'

const severityClasses: Record<Severity, string> = {
  CRÍTICA: 'border-red/80 bg-red/10 text-red',
  ALTA: 'border-orange/80 bg-orange/10 text-orange',
  ADVERTENCIA: 'border-yellow/80 bg-yellow/10 text-yellow',
  MEDIA: 'border-blue/80 bg-blue/10 text-blue',
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        'inline-flex h-5 w-[84px] items-center justify-center rounded-[3px] border text-[9px] leading-none font-medium',
        severityClasses[severity],
      )}
    >
      {severity}
    </span>
  )
}
