import { useCallback, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useWebSocket } from '@/hooks/useWebSocket'
import { formatRelativeTime } from '@/lib/utils'
import { Check, Download, Film, MessageSquare, Subtitles } from 'lucide-react'

interface Activity {
  id: string
  type: string
  message: string
  timestamp: string
}

const typeIcons: Record<string, typeof Check> = {
  'import:complete': Check,
  'download:complete': Download,
  'subtitle:found': Subtitles,
  'request:new': MessageSquare,
  'request:approved': Film,
}

export function ActivityFeed() {
  const [activities, setActivities] = useState<Activity[]>([
    { id: '1', type: 'import:complete', message: 'Ready to track activity', timestamp: new Date().toISOString() },
  ])

  const handleEvent = useCallback((data: unknown) => {
    const d = data as Record<string, string>
    setActivities((prev) => [
      {
        id: Date.now().toString(),
        type: d.event || 'info',
        message: d.title || d.message || 'Event received',
        timestamp: new Date().toISOString(),
      },
      ...prev.slice(0, 19),
    ])
  }, [])

  useWebSocket('import:complete', handleEvent)
  useWebSocket('download:complete', handleEvent)
  useWebSocket('request:new', handleEvent)
  useWebSocket('subtitle:found', handleEvent)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {activities.map((activity) => {
          const Icon = typeIcons[activity.type] || Check
          return (
            <div
              key={activity.id}
              className="flex items-start gap-3 py-2 text-body"
            >
              <Icon size={14} className="text-text-muted mt-0.5 shrink-0" />
              <span className="text-text-secondary flex-1 min-w-0 truncate">
                {activity.message}
              </span>
              <span className="text-caption text-text-muted shrink-0">
                {formatRelativeTime(activity.timestamp)}
              </span>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
