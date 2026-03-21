import { Progress } from '@/components/ui/progress'
import { formatBytes, formatSpeed, formatDuration } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface ProgressBarProps {
  progress: number
  speed?: number
  eta?: number | null
  downloaded?: number
  total?: number
  className?: string
}

export function ProgressBar({ progress, speed, eta, downloaded, total, className }: ProgressBarProps) {
  return (
    <div className={cn('space-y-1', className)}>
      <Progress value={progress} />
      <div className="flex items-center justify-between text-caption text-text-muted">
        <span>{Math.round(progress)}%</span>
        <div className="flex items-center gap-3">
          {downloaded != null && total != null && (
            <span>
              {formatBytes(downloaded)} / {formatBytes(total)}
            </span>
          )}
          {speed != null && speed > 0 && <span>{formatSpeed(speed)}</span>}
          {eta != null && eta > 0 && <span>ETA: {formatDuration(eta)}</span>}
        </div>
      </div>
    </div>
  )
}
