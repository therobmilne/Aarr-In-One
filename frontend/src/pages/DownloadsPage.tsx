import { useEffect, useState } from 'react'
import { Download, Pause, Play, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ProgressBar } from '@/components/shared/ProgressBar'
import { EmptyState } from '@/components/shared/EmptyState'
import { formatBytes } from '@/lib/utils'
import api from '@/lib/api'

interface DownloadItem {
  id: number
  type: string
  status: string
  category: string
  title: string
  indexer_name: string | null
  size_bytes: number
  downloaded_bytes: number
  speed_bytes_sec: number
  progress: number
  eta_seconds: number | null
  seed_ratio: number
  seeds: number
  peers: number
  error_message: string | null
}

export function DownloadsPage() {
  const [downloads, setDownloads] = useState<DownloadItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchDownloads = async () => {
    try {
      const { data } = await api.get('/downloads')
      setDownloads(Array.isArray(data) ? data : [])
    } catch {
      // Not ready
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDownloads()
    const interval = setInterval(fetchDownloads, 3000)
    return () => clearInterval(interval)
  }, [])

  const handlePause = async (id: number) => {
    await api.post(`/downloads/${id}/pause`)
    fetchDownloads()
  }

  const handleResume = async (id: number) => {
    await api.post(`/downloads/${id}/resume`)
    fetchDownloads()
  }

  const handleDelete = async (id: number) => {
    if (confirm('Remove this download?')) {
      await api.delete(`/downloads/${id}`)
      fetchDownloads()
    }
  }

  return (
    <div>
      <PageHeader title="Downloads" subtitle={`${downloads.length} items`} />

      {downloads.length === 0 ? (
        <EmptyState
          icon={Download}
          title="No active downloads"
          description="Downloads will appear here when content is being fetched from indexers."
        />
      ) : (
        <div className="space-y-3">
          {downloads.map((dl) => (
            <Card key={dl.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="text-body text-text-primary font-medium truncate">{dl.title}</span>
                    <Badge>{dl.type}</Badge>
                    <Badge variant={dl.status === 'downloading' ? 'downloading' : dl.status === 'failed' ? 'failed' : 'default'}>
                      {dl.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1 ml-2">
                    {dl.status === 'downloading' && (
                      <Button variant="ghost" size="icon" onClick={() => handlePause(dl.id)}>
                        <Pause size={14} />
                      </Button>
                    )}
                    {dl.status === 'paused' && (
                      <Button variant="ghost" size="icon" onClick={() => handleResume(dl.id)}>
                        <Play size={14} />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(dl.id)}>
                      <Trash2 size={14} className="text-status-error" />
                    </Button>
                  </div>
                </div>
                <ProgressBar
                  progress={dl.progress}
                  speed={dl.speed_bytes_sec}
                  eta={dl.eta_seconds}
                  downloaded={dl.downloaded_bytes}
                  total={dl.size_bytes}
                />
                <div className="flex items-center gap-4 mt-2 text-caption text-text-muted">
                  {dl.indexer_name && <span>From: {dl.indexer_name}</span>}
                  <span>{formatBytes(dl.size_bytes)}</span>
                  {dl.type === 'torrent' && <span>{dl.seeds}S / {dl.peers}P</span>}
                  {dl.seed_ratio > 0 && <span>Ratio: {dl.seed_ratio.toFixed(2)}</span>}
                </div>
                {dl.error_message && (
                  <p className="text-caption text-status-error mt-1">{dl.error_message}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
