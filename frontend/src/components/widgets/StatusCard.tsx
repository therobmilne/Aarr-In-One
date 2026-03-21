import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

interface StatusCardProps {
  icon: LucideIcon
  label: string
  value: string
  status?: 'success' | 'warning' | 'error' | 'info'
  subtitle?: string
}

const statusColors = {
  success: 'text-status-success bg-status-success/10',
  warning: 'text-status-warning bg-status-warning/10',
  error: 'text-status-error bg-status-error/10',
  info: 'text-status-info bg-status-info/10',
}

export function StatusCard({ icon: Icon, label, value, status = 'info', subtitle }: StatusCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className={cn('w-10 h-10 rounded-sm flex items-center justify-center', statusColors[status])}>
          <Icon size={20} />
        </div>
        <div className="min-w-0">
          <p className="text-caption text-text-muted">{label}</p>
          <p className="text-card-title text-text-primary truncate">{value}</p>
          {subtitle && <p className="text-caption text-text-muted">{subtitle}</p>}
        </div>
      </CardContent>
    </Card>
  )
}
