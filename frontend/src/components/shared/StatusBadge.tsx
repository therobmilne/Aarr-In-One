import { Badge } from '@/components/ui/badge'
import { STATUS_BG_COLORS } from '@/lib/constants'

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const variant = (status.toLowerCase() in STATUS_BG_COLORS
    ? status.toLowerCase()
    : 'default') as keyof typeof STATUS_BG_COLORS | 'default'

  return (
    <Badge variant={variant} className={className}>
      {status}
    </Badge>
  )
}
