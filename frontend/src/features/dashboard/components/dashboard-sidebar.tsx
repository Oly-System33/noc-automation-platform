import { ChevronDown, CircleUserRound } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import nocLogo from '@/assets/noc-logo.png'
import { SystemStatus } from '@/features/dashboard/components/system-status'
import { navigationItems } from '@/features/dashboard/data/dashboard-visual-data'
import type { HealthIndicatorState } from '@/features/dashboard/types/dashboard-ui'
import { cn } from '@/lib/utils'

type DashboardSidebarProps = {
  apiState: HealthIndicatorState
  databaseState: HealthIndicatorState
}

export function DashboardSidebar({
  apiState,
  databaseState,
}: DashboardSidebarProps) {
  return (
    <aside className="sticky top-0 flex h-svh w-[220px] shrink-0 flex-col border-r border-border bg-sidebar px-2 py-3">
      <div className="flex h-10 items-center gap-2 px-2">
        <img
          src={nocLogo}
          alt="Logo NOC"
          className="size-9 shrink-0 object-contain"
        />
        <div className="min-w-0">
          <div className="text-[18px] leading-5 font-medium text-text-primary">
            NOC
          </div>
          <div className="truncate text-[9px] text-text-muted">
            Plataforma de Automatización
          </div>
        </div>
      </div>

      <nav aria-label="Navegación principal" className="mt-4 space-y-1">
        {navigationItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                cn(
                  'flex h-9 items-center gap-3 rounded-md border border-transparent px-3 text-[12px] text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary',
                  isActive &&
                    'border-primary bg-primary-muted text-text-primary shadow-[inset_0_0_16px_rgb(124_58_237/10%)]',
                )
              }
            >
              <Icon aria-hidden="true" className="size-[17px] shrink-0" />
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="mt-auto">
        <SystemStatus apiState={apiState} databaseState={databaseState} />
      </div>

      <section className="mt-[clamp(40px,13vh,120px)] overflow-hidden rounded-md border border-border bg-surface/70 text-[10px]">
        <div className="flex items-center gap-2 border-b border-border-subtle p-2.5">
          <CircleUserRound
            aria-hidden="true"
            className="size-6 shrink-0 text-text-secondary"
          />
          <div className="min-w-0 flex-1">
            <div className="text-[11px] text-text-primary">Operador NOC</div>
            <div className="truncate text-[8px] text-text-muted">
              noc.operador@demo.com
            </div>
          </div>
          <ChevronDown aria-hidden="true" className="size-3.5 text-text-muted" />
        </div>
        <div className="flex items-center gap-2 px-3 py-2 text-text-secondary">
          <span className="size-2 rounded-full bg-green" />
          En línea
        </div>
      </section>
    </aside>
  )
}
