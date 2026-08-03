import type { ReactNode } from 'react'
import { RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'

export const fieldClass = 'h-8 rounded-md border border-border bg-background px-2 text-xs text-text-primary placeholder:text-text-muted'

export function PageHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return <header className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-xl font-medium text-text-primary">{title}</h1><p className="mt-1 text-xs text-text-muted">{description}</p></div>{actions}</header>
}

export function FilterBar({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-end gap-2 rounded-md border border-border bg-surface p-3">{children}</div>
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="flex min-w-[130px] flex-col gap-1 text-[10px] text-text-muted"><span>{label}</span>{children}</label>
}

export function TableState({ colSpan, isLoading, isError, isEmpty, onRetry, emptyText }: { colSpan: number; isLoading: boolean; isError: boolean; isEmpty: boolean; onRetry: () => void; emptyText: string }) {
  if (isLoading) return <>{Array.from({ length: 6 }, (_, index) => <tr key={index} data-testid="table-skeleton" className="h-10 border-b border-border-subtle"><td colSpan={colSpan} className="px-3"><span className="block h-3 animate-pulse rounded bg-text-muted/15" /></td></tr>)}</>
  if (isError) return <tr><td colSpan={colSpan} className="h-48 text-center"><div role="alert" className="inline-flex items-center gap-3 text-xs text-red">No fue posible cargar los datos.<Button type="button" size="xs" variant="outline" onClick={onRetry}><RefreshCw aria-hidden="true" />Reintentar</Button></div></td></tr>
  if (isEmpty) return <tr><td colSpan={colSpan} className="h-48 text-center text-xs text-text-muted">{emptyText}</td></tr>
  return null
}

export function TablePagination({ total, limit, offset, onChange, disabled }: { total: number; limit: number; offset: number; onChange: (offset: number) => void; disabled?: boolean }) {
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(offset + limit, total)
  return <nav aria-label="Paginación" className="flex items-center justify-between border-t border-border-subtle px-3 py-2 text-[11px] text-text-muted"><span>{from}-{to} de {total}</span><div className="flex gap-2"><Button type="button" size="xs" variant="outline" disabled={disabled || offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>Anterior</Button><Button type="button" size="xs" variant="outline" disabled={disabled || offset + limit >= total} onClick={() => onChange(offset + limit)}>Siguiente</Button></div></nav>
}

export function PageCard({ children }: { children: ReactNode }) {
  return <section className="overflow-hidden rounded-md border border-border bg-surface">{children}</section>
}
