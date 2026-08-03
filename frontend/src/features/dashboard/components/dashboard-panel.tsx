import type { ReactNode } from 'react'

import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { PanelHeader } from '@/features/dashboard/components/panel-header'
import { AppLink } from '@/components/app-link'

type DashboardPanelProps = {
  title: string
  count?: number
  children: ReactNode
  footer?: string
  className?: string
  isRefreshing?: boolean
  hasError?: boolean
  onRetry?: () => void
  href: string
  footerHref?: string
}

export function DashboardPanel({
  title,
  count,
  children,
  footer,
  className,
  isRefreshing = false,
  hasError = false,
  onRetry,
  href,
  footerHref,
}: DashboardPanelProps) {
  return (
    <Card
      className={cn(
        'h-full min-h-0 gap-0 overflow-hidden rounded-md border border-border bg-surface py-0 ring-0',
        className,
      )}
    >
      <PanelHeader
        title={title}
        count={count}
        isRefreshing={isRefreshing}
        hasError={hasError}
        onRetry={onRetry}
        href={href}
      />
      {children}
      {footer && (
        <AppLink
          href={footerHref ?? href}
          className="mt-auto flex h-7 w-full shrink-0 items-center justify-between border-t border-border-subtle px-3 text-left text-[10px] text-text-muted transition-colors hover:bg-surface-hover hover:text-text-secondary"
        >
          {footer}
          <span aria-hidden="true" className="text-base leading-none">
            ›
          </span>
        </AppLink>
      )}
    </Card>
  )
}
