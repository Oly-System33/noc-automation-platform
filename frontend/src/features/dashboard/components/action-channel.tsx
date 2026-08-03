import {
  Diamond,
  Mail,
  MessageSquare,
  Phone,
  Send,
  SquareTerminal,
} from 'lucide-react'

import { cn } from '@/lib/utils'
import type { ActionKind } from '@/features/dashboard/types/dashboard-ui'

const actionConfig = {
  jira: { icon: Diamond, label: 'jira', className: 'text-blue' },
  calls: { icon: Phone, label: 'calls', className: 'text-green' },
  telegram: { icon: Send, label: 'telegram', className: 'text-cyan' },
  email: { icon: Mail, label: 'email', className: 'text-text-secondary' },
  script: {
    icon: SquareTerminal,
    label: 'script',
    className: 'text-text-secondary',
  },
  teams: {
    icon: MessageSquare,
    label: 'teams',
    className: 'text-purple',
  },
} satisfies Record<
  ActionKind | 'teams',
  { icon: typeof Diamond; label: string; className: string }
>

export function ActionChannel({ action }: { action: string | null }) {
  if (!action) {
    return <span className="text-text-muted">—</span>
  }

  const normalizedAction = action.toLowerCase()
  const actionKey = Object.keys(actionConfig).find((key) =>
    normalizedAction.includes(key),
  ) as keyof typeof actionConfig | undefined
  const config = actionKey ? actionConfig[actionKey] : undefined
  const Icon = config?.icon

  return (
    <span
      className="inline-flex max-w-full items-center gap-2 whitespace-nowrap"
      title={action}
    >
      {Icon && (
        <Icon
          aria-hidden="true"
          className={cn('size-4 shrink-0', config?.className)}
        />
      )}
      <span className="truncate">{action}</span>
    </span>
  )
}
