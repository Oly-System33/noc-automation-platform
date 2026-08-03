import { AlertCircle, ChevronRight, RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'

type PanelHeaderProps = {
  title: string
  count?: number
  actionLabel?: string
  isRefreshing?: boolean
  hasError?: boolean
  onRetry?: () => void
}

export function PanelHeader({
  title,
  count,
  actionLabel = 'Ver todas',
  isRefreshing = false,
  hasError = false,
  onRetry,
}: PanelHeaderProps) {
  return (
    <header className="flex h-8 shrink-0 items-center justify-between border-b border-border-subtle px-3">
      <div className="flex items-center gap-2">
        <h2 className="text-[15px] leading-none font-medium text-text-primary">
          {title}
        </h2>
        {count !== undefined && (
          <span
            aria-label={`${count} elementos`}
            className="inline-flex size-5 items-center justify-center rounded-[3px] border border-primary-hover bg-primary-muted text-[11px] font-medium text-text-primary"
          >
            {count}
          </span>
        )}
        {isRefreshing && (
          <RefreshCw
            aria-label="Actualizando"
            className="size-3 animate-spin text-cyan"
          />
        )}
        {hasError && (
          <AlertCircle
            aria-label="Actualización fallida"
            className="size-3 text-red"
          />
        )}
      </div>
      <div className="flex items-center gap-1.5">
        {hasError && onRetry && (
          <Button
            type="button"
            variant="outline"
            size="xs"
            onClick={onRetry}
            className="h-6 rounded-[3px] border-red/50 bg-transparent px-2 text-[9px] text-red hover:bg-red/10"
          >
            Reintentar
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="xs"
          className="h-6 rounded-[3px] border-border bg-transparent px-2 text-[10px] text-text-secondary hover:bg-surface-hover hover:text-text-primary"
        >
          {actionLabel}
          <ChevronRight aria-hidden="true" className="size-3" />
        </Button>
      </div>
    </header>
  )
}
