import { KpiCard } from '@/features/dashboard/components/kpi-card'
import { kpiItems } from '@/features/dashboard/data/dashboard-mock-data'

export function KpiGrid() {
  return (
    <section
      aria-label="Indicadores principales"
      className="grid grid-cols-8 gap-2"
    >
      {kpiItems.map((item) => (
        <KpiCard key={item.id} item={item} />
      ))}
    </section>
  )
}
