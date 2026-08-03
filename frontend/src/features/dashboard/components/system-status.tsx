import { ChevronUp, Server } from 'lucide-react'

export function SystemStatus() {
  return (
    <section className="rounded-md border border-border bg-surface/70 p-3 text-[10px]">
      <div className="mb-3 flex items-center justify-between text-text-secondary">
        <div className="flex items-center gap-2">
          <span className="size-2 rounded-full bg-green" />
          <h2 className="font-normal">Estado del sistema</h2>
        </div>
        <ChevronUp aria-hidden="true" className="size-3.5" />
      </div>
      <div className="space-y-2.5 text-text-secondary">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Server aria-hidden="true" className="size-3.5" />
            API
          </span>
          <span className="flex items-center gap-1.5 text-green">
            <span className="size-2 rounded-full bg-green" /> OK
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-green" />
            Operativo
          </span>
          <span className="flex items-center gap-1.5 text-green">
            <span className="size-2 rounded-full bg-green" /> OK
          </span>
        </div>
      </div>
    </section>
  )
}
