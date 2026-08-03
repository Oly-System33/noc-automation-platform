import { Button } from '@/components/ui/button'
import { KpiCard } from '@/features/dashboard/components/kpi-card'
import type { DashboardStatusCounts } from '@/features/dashboard/api/dashboard-api.types'
import { mapSummaryCountsToKpis } from '@/features/dashboard/mappers/dashboard-data.mapper'

type KpiGridProps = {
  counts?: DashboardStatusCounts
  isLoading: boolean
  isError: boolean
  isRetrying: boolean
  onRetry: () => void
}

export function KpiGrid({
  counts,
  isLoading,
  isError,
  isRetrying,
  onRetry,
}: KpiGridProps) {
  const items = mapSummaryCountsToKpis(counts)

  return (
    <div className="relative">
      <section
        aria-label="Indicadores principales"
        className="grid grid-cols-8 gap-2"
      >
        {items.map((item) => (
          <KpiCard key={item.id} item={item} isLoading={isLoading} />
        ))}
      </section>
      {isError && (
        <div
          role="alert"
          className="absolute right-1 bottom-1 flex items-center gap-2 rounded-sm border border-red/50 bg-surface-elevated px-2 py-1 text-[9px] text-red"
        >
          {counts
            ? 'No fue posible actualizar los indicadores'
            : 'No fue posible cargar los indicadores'}
          <Button
            type="button"
            variant="outline"
            size="xs"
            disabled={isRetrying}
            onClick={onRetry}
            className="h-5 rounded-[3px] border-red/50 bg-transparent px-1.5 text-[9px] text-text-primary hover:bg-red/10"
          >
            Reintentar
          </Button>
        </div>
      )}
    </div>
  )
}
