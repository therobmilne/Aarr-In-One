import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ErrorStateProps {
  title?: string
  message: string
  tips?: string[]
  onRetry?: () => void
  onSettings?: () => void
  className?: string
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  tips,
  onRetry,
  onSettings,
  className,
}: ErrorStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-2xl text-center', className)}>
      <div className="w-16 h-16 rounded-full bg-status-error/10 flex items-center justify-center mb-lg">
        <AlertTriangle size={28} className="text-status-error" />
      </div>
      <h3 className="text-section-header text-text-primary mb-2">{title}</h3>
      <p className="text-body text-text-secondary max-w-md mb-4">{message}</p>
      {tips && tips.length > 0 && (
        <ul className="text-body text-text-secondary text-left mb-lg max-w-md">
          {tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-2 mb-1">
              <span className="text-text-muted">&#8226;</span>
              {tip}
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-3">
        {onRetry && <Button onClick={onRetry}>Retry</Button>}
        {onSettings && (
          <Button variant="secondary" onClick={onSettings}>
            Go to Settings
          </Button>
        )}
      </div>
    </div>
  )
}
