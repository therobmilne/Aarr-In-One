import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ProgressBar } from '@/components/shared/ProgressBar'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'

interface DownloadItem {
  id: number
  title: string
  type: string
  status: string
  progress: number
  speed_bytes_sec: number
  eta_seconds: number | null
  downloaded_bytes: number
  size_bytes: number
}

export function DownloadQueue() {
  const [downloads, setDownloads] = useState<DownloadItem[]>([])

  useEffect(() => {
    const fetchDownloads = async () => {
      try {
        const { data } = await api.get('/downloads', { params: { limit: 5 } })
        setDownloads(data)
      } catch {
        // API not available yet
      }
    }
    fetchDownloads()
    const interval = setInterval(fetchDownloads, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Active Downloads</CardTitle>
        {downloads.length > 0 && (
          <a href="/downloads" className="text-caption text-accent-primary hover:text-accent-hover">
            See All
          </a>
        )}
      </CardHeader>
      <CardContent>
        {downloads.length === 0 ? (
          <p className="text-body text-text-muted py-4 text-center">No active downloads</p>
        ) : (
          <div className="space-y-4">
            {downloads.map((dl) => (
              <div key={dl.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-body text-text-primary truncate flex-1 mr-2">
                    {dl.title}
                  </span>
                  <Badge variant={dl.status === 'downloading' ? 'downloading' : 'default'}>
                    {dl.type}
                  </Badge>
                </div>
                <ProgressBar
                  progress={dl.progress}
                  speed={dl.speed_bytes_sec}
                  eta={dl.eta_seconds}
                  downloaded={dl.downloaded_bytes}
                  total={dl.size_bytes}
                />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
