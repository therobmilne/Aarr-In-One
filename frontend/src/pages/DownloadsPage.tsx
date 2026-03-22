import { useEffect, useState } from 'react'
import { Download, Pause, Play, Trash2, ArrowDown, ArrowUp, Film, Tv } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { EmptyState } from '@/components/shared/EmptyState'
import { formatBytes, formatSpeed, formatDuration } from '@/lib/utils'
import api from '@/lib/api'

interface DownloadItem {
  id: string
  name: string
  type: string
  status: string
  category: string
  size: number
  progress: number
  download_speed: number
  upload_speed: number
  seeds: number
  peers: number
  eta: number | string
  ratio: number
}

export function DownloadsPage() {
  const [downloads, setDownloads] = useState<DownloadItem[]>([])
  const [loading, setLoading] = useState(true)
  const [totalDown, setTotalDown] = useState(0)
  const [totalUp, setTotalUp] = useState(0)

  const fetchDownloads = async () => {
    try {
      const { data } = await api.get('/downloads')
      const items = Array.isArray(data) ? data : []
      setDownloads(items)
      setTotalDown(items.reduce((s: number, d: DownloadItem) => s + (d.download_speed || 0), 0))
      setTotalUp(items.reduce((s: number, d: DownloadItem) => s + (d.upload_speed || 0), 0))
    } catch { /* not ready */ }
    finally { setLoading(false) }
  }

  useEffect(() => {
    fetchDownloads()
    const interval = setInterval(fetchDownloads, 3000)
    return () => clearInterval(interval)
  }, [])

  const handlePause = async (id: string) => { await api.post(`/downloads/${id}/pause`); fetchDownloads() }
  const handleResume = async (id: string) => { await api.post(`/downloads/${id}/resume`); fetchDownloads() }
  const handleDelete = async (id: string) => {
    if (confirm('Remove this download?')) { await api.delete(`/downloads/${id}`); fetchDownloads() }
  }

  const activeCount = downloads.filter((d) => d.status === 'downloading' || d.status === 'seeding').length

  const getCategoryIcon = (cat: string) => {
    if (cat === 'radarr' || cat === 'movies' || cat === 'movie') return <Film size={14} className="text-status-info" />
    if (cat === 'sonarr' || cat === 'tv') return <Tv size={14} className="text-status-warning" />
    return <Download size={14} className="text-text-muted" />
  }

  const getStatusColor = (status: string) => {
    if (status === 'downloading') return 'downloading'
    if (status === 'seeding') return 'healthy'
    if (status === 'completed' || status === 'importing') return 'available'
    if (status === 'failed' || status === 'error') return 'failed'
    if (status === 'paused') return 'warning'
    return 'default' as const
  }

  const formatEta = (eta: number | string) => {
    if (typeof eta === 'string') return eta || '--'
    if (!eta || eta <= 0 || eta === 8640000) return '--'
    return formatDuration(eta)
  }

  return (
    <div>
      <PageHeader title="Downloads" subtitle={`${downloads.length} items`} />

      {/* Top status bar */}
      <div className="flex items-center gap-6 mb-6 bg-bg-surface rounded-md border border-bg-elevated p-3">
        <div className="flex items-center gap-2">
          <ArrowDown size={14} className="text-status-info" />
          <span className="text-body text-text-secondary">
            {formatSpeed(totalDown)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ArrowUp size={14} className="text-status-success" />
          <span className="text-body text-text-secondary">
            {formatSpeed(totalUp)}
          </span>
        </div>
        <span className="text-body text-text-muted">
          {activeCount} active
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-status-success" />
          <a href="/vpn" className="text-caption text-text-muted hover:text-accent-primary">VPN</a>
        </div>
      </div>

      {downloads.length === 0 ? (
        <EmptyState
          icon={Download}
          title="No active downloads"
          description="Downloads will appear here when content is being fetched."
        />
      ) : (
        <div className="space-y-2">
          {/* Header row */}
          <div className="hidden md:grid grid-cols-12 gap-2 px-4 py-2 text-caption text-text-muted uppercase">
            <div className="col-span-5">Name</div>
            <div className="col-span-1">Type</div>
            <div className="col-span-1">Size</div>
            <div className="col-span-2">Progress</div>
            <div className="col-span-1">Speed</div>
            <div className="col-span-1">ETA</div>
            <div className="col-span-1">Actions</div>
          </div>

          {downloads.map((dl) => (
            <Card key={dl.id}>
              <CardContent className="p-3">
                <div className="md:grid md:grid-cols-12 md:gap-2 md:items-center space-y-2 md:space-y-0">
                  {/* Name + category */}
                  <div className="col-span-5 flex items-center gap-2 min-w-0">
                    {getCategoryIcon(dl.category)}
                    <span className="text-body font-medium text-text-primary truncate">{dl.name}</span>
                  </div>

                  {/* Type */}
                  <div className="col-span-1">
                    <Badge variant={getStatusColor(dl.status)}>
                      {dl.type === 'torrent' ? 'Torrent' : 'Usenet'}
                    </Badge>
                  </div>

                  {/* Size */}
                  <div className="col-span-1 text-caption text-text-muted">
                    {formatBytes(dl.size)}
                  </div>

                  {/* Progress */}
                  <div className="col-span-2">
                    <div className="flex items-center gap-2">
                      <Progress value={dl.progress} className="flex-1" />
                      <span className="text-caption text-text-muted w-10 text-right">
                        {Math.round(dl.progress)}%
                      </span>
                    </div>
                    {dl.type === 'torrent' && dl.seeds > 0 && (
                      <span className="text-[10px] text-text-muted">{dl.seeds}S / {dl.peers}P</span>
                    )}
                  </div>

                  {/* Speed */}
                  <div className="col-span-1 text-caption text-text-muted">
                    {dl.status === 'downloading' ? formatSpeed(dl.download_speed) : '--'}
                  </div>

                  {/* ETA */}
                  <div className="col-span-1 text-caption text-text-muted">
                    {formatEta(dl.eta)}
                  </div>

                  {/* Actions */}
                  <div className="col-span-1 flex items-center gap-0.5">
                    {dl.status === 'downloading' && (
                      <Button variant="ghost" size="icon" onClick={() => handlePause(dl.id)} title="Pause">
                        <Pause size={14} />
                      </Button>
                    )}
                    {dl.status === 'paused' && (
                      <Button variant="ghost" size="icon" onClick={() => handleResume(dl.id)} title="Resume">
                        <Play size={14} />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(dl.id)} title="Remove">
                      <Trash2 size={14} className="text-status-error" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
