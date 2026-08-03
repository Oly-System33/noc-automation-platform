import { Dialog as DialogPrimitive } from 'radix-ui'
import { X } from 'lucide-react'

import { useInterventionRunbookQuery } from '@/features/dashboard/api/dashboard-queries'
import type { ManualIntervention } from '@/features/dashboard/types/dashboard-ui'

export function RunbookDialog({
  intervention,
  open,
  onOpenChange,
}: {
  intervention: ManualIntervention | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const query = useInterventionRunbookQuery(
    intervention?.interventionId ?? '',
    open && intervention !== null,
  )

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-background/80" />
        <DialogPrimitive.Content className="fixed top-1/2 left-1/2 z-50 w-[min(560px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-md border border-border bg-surface-elevated p-5 text-text-secondary shadow-2xl focus:outline-none">
          <DialogPrimitive.Title className="text-base font-medium text-text-primary">
            Runbook asociado
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-1 text-[11px] text-text-muted">
            Vista operativa segura para {intervention?.eventId ?? 'la intervención'}.
          </DialogPrimitive.Description>
          <DialogPrimitive.Close className="absolute top-4 right-4" aria-label="Cerrar runbook">
            <X aria-hidden="true" className="size-4" />
          </DialogPrimitive.Close>

          <div className="mt-4 min-h-32 text-[12px]">
            {query.isPending && <p role="status">Cargando runbook...</p>}
            {query.isError && <p role="alert" className="text-red">Runbook no disponible.</p>}
            {query.data && (
              <dl className="grid grid-cols-[130px_1fr] gap-x-4 gap-y-2">
                <dt className="text-text-muted">Fuente</dt><dd>{query.data.source === 'persisted_action_plan' ? 'Plan persistido' : 'Runbook actual'}</dd>
                <dt className="text-text-muted">Acciones</dt><dd>{query.data.actions.join(', ') || '—'}</dd>
                <dt className="text-text-muted">Objetivo</dt><dd>{query.data.target ?? '—'}</dd>
                <dt className="text-text-muted">Demora</dt><dd>{query.data.delay_minutes === null ? '—' : `${query.data.delay_minutes}m`}</dd>
                <dt className="text-text-muted">Ejecución</dt><dd>{query.data.execution_mode ?? '—'}</dd>
                <dt className="text-text-muted">Aprobación</dt><dd>{query.data.approval_when ?? '—'}</dd>
                <dt className="text-text-muted">Preacciones</dt><dd>{query.data.pre_actions.join(', ') || '—'}</dd>
                {query.data.warning && <><dt className="text-text-muted">Aviso</dt><dd>{query.data.warning}</dd></>}
              </dl>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
