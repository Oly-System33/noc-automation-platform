import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ApprovalsTable } from '@/features/dashboard/components/approvals-table'
import { ManualInterventionTable } from '@/features/dashboard/components/manual-intervention-table'
import { OperationsTable } from '@/features/dashboard/components/operations-table'

const common = {
  hasResponse: true,
  isLoading: false,
  isError: false,
  isFetching: false,
  pendingId: null,
  onRetry: vi.fn(),
}

describe('estados de paneles operativos', () => {
  it('muestra los tres estados vacíos sin fallback mock', () => {
    render(<><OperationsTable {...common} operations={[]} onPause={vi.fn()} onResume={vi.fn()} /><ApprovalsTable {...common} approvals={[]} onApprove={vi.fn()} onReject={vi.fn()} /><ManualInterventionTable interventions={[]} hasResponse isLoading={false} isError={false} isFetching={false} pendingId={null} onRetryList={vi.fn()} onViewRunbook={vi.fn()} onRetryIntervention={vi.fn()} /></>)

    expect(screen.getByText('No hay operaciones activas')).toBeInTheDocument()
    expect(screen.getByText('No hay aprobaciones pendientes')).toBeInTheDocument()
    expect(screen.getByText('No hay intervenciones manuales pendientes')).toBeInTheDocument()
  })

  it('mantiene filas skeleton durante carga', () => {
    render(<><OperationsTable {...common} hasResponse={false} isLoading operations={[]} onPause={vi.fn()} onResume={vi.fn()} /><ApprovalsTable {...common} hasResponse={false} isLoading approvals={[]} onApprove={vi.fn()} onReject={vi.fn()} /><ManualInterventionTable interventions={[]} hasResponse={false} isLoading isError={false} isFetching pendingId={null} onRetryList={vi.fn()} onViewRunbook={vi.fn()} onRetryIntervention={vi.fn()} /></>)

    expect(screen.getAllByTestId('operation-skeleton')).toHaveLength(5)
    expect(screen.getAllByTestId('approval-skeleton')).toHaveLength(3)
    expect(screen.getAllByTestId('intervention-skeleton')).toHaveLength(3)
  })

  it('aísla los errores por sección y ofrece reintento', () => {
    render(<><OperationsTable {...common} hasResponse={false} isError operations={[]} onPause={vi.fn()} onResume={vi.fn()} /><ApprovalsTable {...common} approvals={[]} onApprove={vi.fn()} onReject={vi.fn()} /><ManualInterventionTable interventions={[]} hasResponse isLoading={false} isError={false} isFetching={false} pendingId={null} onRetryList={vi.fn()} onViewRunbook={vi.fn()} onRetryIntervention={vi.fn()} /></>)

    expect(screen.getByText('No fue posible cargar las operaciones.')).toBeInTheDocument()
    expect(screen.getByText('No hay aprobaciones pendientes')).toBeInTheDocument()
    expect(screen.getByText('No hay intervenciones manuales pendientes')).toBeInTheDocument()
  })
})
