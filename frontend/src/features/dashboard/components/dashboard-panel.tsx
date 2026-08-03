import type { ReactNode } from 'react'

import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { PanelHeader } from '@/features/dashboard/components/panel-header'

type DashboardPanelProps = {
  title: string
  count?: number
  children: ReactNode
  footer?: string
  className?: string
}

export function DashboardPanel({
  title,
  count,
  children,
  footer,
  className,
}: DashboardPanelProps) {
  return (
    <Card
      className={cn(
        'gap-0 overflow-hidden rounded-md border border-border bg-surface py-0 ring-0',
        className,
      )}
    >
      <PanelHeader title={title} count={count} />
      {children}
      {footer && (
        <button
          type="button"
          className="mt-auto flex h-7 w-full items-center justify-between border-t border-border-subtle px-3 text-left text-[10px] text-text-muted transition-colors hover:bg-surface-hover hover:text-text-secondary"
        >
          {footer}
          <span aria-hidden="true" className="text-base leading-none">
            ›
          </span>
        </button>
      )}
    </Card>
  )
}
