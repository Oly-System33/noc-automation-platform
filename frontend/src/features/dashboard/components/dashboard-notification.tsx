import { X } from 'lucide-react'

import { cn } from '@/lib/utils'

export type DashboardNotice = {
  id: number
  tone: 'success' | 'error' | 'info'
  message: string
}

export function DashboardNotification({
  notice,
  onClose,
}: {
  notice: DashboardNotice | null
  onClose: () => void
}) {
  if (!notice) return null

  return (
    <div
      role={notice.tone === 'error' ? 'alert' : 'status'}
      className={cn(
        'fixed top-3 right-3 z-50 flex max-w-sm items-center gap-3 rounded-md border bg-surface-elevated px-3 py-2 text-[11px] shadow-lg',
        notice.tone === 'success' && 'border-green/60 text-green',
        notice.tone === 'error' && 'border-red/60 text-red',
        notice.tone === 'info' && 'border-blue/60 text-blue',
      )}
    >
      <span>{notice.message}</span>
      <button type="button" aria-label="Cerrar notificación" onClick={onClose}>
        <X aria-hidden="true" className="size-3.5" />
      </button>
    </div>
  )
}
