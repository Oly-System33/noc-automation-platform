import { ChevronRight } from 'lucide-react'

import { Button } from '@/components/ui/button'

type PanelHeaderProps = {
  title: string
  count?: number
  actionLabel?: string
}

export function PanelHeader({
  title,
  count,
  actionLabel = 'Ver todas',
}: PanelHeaderProps) {
  return (
    <header className="flex h-8 items-center justify-between border-b border-border-subtle px-3">
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
      </div>
      <Button
        type="button"
        variant="outline"
        size="xs"
        className="h-6 rounded-[3px] border-border bg-transparent px-2 text-[10px] text-text-secondary hover:bg-surface-hover hover:text-text-primary"
      >
        {actionLabel}
        <ChevronRight aria-hidden="true" className="size-3" />
      </Button>
    </header>
  )
}
