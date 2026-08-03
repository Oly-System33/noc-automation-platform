import type { CSSProperties } from 'react'

import { Card } from '@/components/ui/card'
import type { KpiItem, KpiTone } from '@/features/dashboard/types/dashboard-ui'

const toneVariables: Record<KpiTone, string> = {
  cyan: 'var(--cyan)',
  teal: 'var(--cyan)',
  purple: 'var(--purple)',
  green: 'var(--green)',
  yellow: 'var(--yellow)',
  orange: 'var(--orange)',
  red: 'var(--red)',
  slate: 'var(--text-secondary)',
}

type KpiCardProps = {
  item: KpiItem
  isLoading?: boolean
}

export function KpiCard({ item, isLoading = false }: KpiCardProps) {
  const Icon = item.icon
  const style = {
    '--kpi-accent': toneVariables[item.tone],
  } as CSSProperties

  return (
    <Card
      data-testid="kpi-card"
      data-size="uniform"
      aria-label={`${item.label}: ${item.value ?? 'sin datos'}`}
      style={style}
      className="h-[78px] min-w-0 gap-0 rounded-md border border-border bg-surface px-3 py-2.5 ring-0"
    >
      <div className="flex min-w-0 items-start gap-2 text-[var(--kpi-accent)]">
        <Icon aria-hidden="true" className="mt-0.5 size-[19px] shrink-0" />
        <div className="min-w-0 text-center">
          <div className="text-[20px] leading-5 font-medium text-text-primary">
            {isLoading ? (
              <span
                aria-label={`Cargando ${item.label}`}
                className="inline-block h-4 w-6 animate-pulse rounded-sm bg-text-muted/30"
              />
            ) : (
              (item.value ?? '—')
            )}
          </div>
          <div className="mt-1 truncate text-[10px] leading-none text-text-secondary">
            {item.label}
          </div>
        </div>
      </div>
      <svg
        aria-hidden="true"
        viewBox="0 0 92 20"
        className="mt-auto h-4 w-full overflow-visible text-[var(--kpi-accent)]"
        preserveAspectRatio="none"
      >
        <path
          d={item.trendPath}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.25"
          vectorEffect="non-scaling-stroke"
        />
        <path
          d="M2 18 H90"
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.12"
          strokeWidth="1"
        />
      </svg>
    </Card>
  )
}
