import { Clock3, Database, RefreshCw } from 'lucide-react'

function HeaderControl({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-7 items-center gap-2 rounded-md border border-border bg-surface px-3 text-[10px] text-text-secondary">
      {children}
    </div>
  )
}

export function DashboardHeader() {
  return (
    <header className="flex min-h-8 items-center justify-between gap-4">
      <h1 className="text-[24px] leading-none font-semibold tracking-[-0.025em] text-text-primary">
        Dashboard principal
      </h1>
      <div className="flex shrink-0 items-center gap-2" aria-label="Estado general">
        <HeaderControl>
          <span className="size-2 rounded-full border border-cyan" />
          <span>FastAPI</span>
          <span className="size-2 rounded-full bg-green" />
          <span className="sr-only">operativo</span>
        </HeaderControl>
        <HeaderControl>
          <Database aria-hidden="true" className="size-3.5" />
          <span>DB</span>
          <span className="size-2 rounded-full bg-green" />
          <span className="sr-only">operativa</span>
        </HeaderControl>
        <HeaderControl>
          <RefreshCw aria-hidden="true" className="size-3.5" />
          <span>15s</span>
        </HeaderControl>
        <HeaderControl>
          <Clock3 aria-hidden="true" className="size-3.5" />
          <span>12:04</span>
        </HeaderControl>
      </div>
    </header>
  )
}
