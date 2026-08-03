import {
  Diamond,
  Mail,
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
} satisfies Record<
  ActionKind,
  { icon: typeof Diamond; label: string; className: string }
>

export function ActionChannel({ action }: { action: ActionKind }) {
  const config = actionConfig[action]
  const Icon = config.icon

  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <Icon aria-hidden="true" className={cn('size-4', config.className)} />
      <span>{config.label}</span>
    </span>
  )
}
