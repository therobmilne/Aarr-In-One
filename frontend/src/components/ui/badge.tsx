import { cn } from '@/lib/utils'
import { STATUS_BG_COLORS } from '@/lib/constants'

interface BadgeProps {
  children: React.ReactNode
  variant?: keyof typeof STATUS_BG_COLORS | 'default'
  className?: string
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-sm px-2 py-0.5 text-badge uppercase',
        variant === 'default'
          ? 'bg-bg-elevated text-text-secondary'
          : STATUS_BG_COLORS[variant] || 'bg-bg-elevated text-text-secondary',
        className
      )}
    >
      {children}
    </span>
  )
}
