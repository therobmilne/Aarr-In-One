import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description: string
  action?: { label: string; onClick: () => void }
  secondaryAction?: { label: string; onClick: () => void }
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-2xl text-center', className)}>
      {Icon && (
        <div className="w-16 h-16 rounded-full bg-bg-elevated flex items-center justify-center mb-lg">
          <Icon size={28} className="text-text-muted" />
        </div>
      )}
      <h3 className="text-section-header text-text-primary mb-2">{title}</h3>
      <p className="text-body text-text-secondary max-w-md mb-lg">{description}</p>
      <div className="flex gap-3">
        {action && (
          <Button onClick={action.onClick}>{action.label}</Button>
        )}
        {secondaryAction && (
          <Button variant="secondary" onClick={secondaryAction.onClick}>
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  )
}
