import { useEffect, useState } from 'react'
import { Radio, Plus } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/shared/EmptyState'
import api from '@/lib/api'

interface Channel {
  id: number
  name: string
  channel_number: number | null
  group: string | null
  logo_url: string | null
  enabled: boolean
  category: string | null
}

export function LiveTVPage() {
  const [channels, setChannels] = useState<Channel[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchChannels = async () => {
      try {
        const { data } = await api.get('/livetv/channels')
        setChannels(data)
      } catch {
        // Not ready
      } finally {
        setLoading(false)
      }
    }
    fetchChannels()
  }, [])

  const groups = [...new Set(channels.map((c) => c.group || 'Uncategorized'))]

  return (
    <div>
      <PageHeader title="Live TV" subtitle={`${channels.length} channels`}>
        <Button><Plus size={16} className="mr-1" /> Add Playlist</Button>
      </PageHeader>

      {channels.length === 0 ? (
        <EmptyState
          icon={Radio}
          title="No IPTV channels configured"
          description="Import an M3U playlist to start watching Live TV through Jellyfin."
          action={{ label: 'Import Playlist', onClick: () => {} }}
        />
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <div key={group}>
              <h2 className="text-section-header text-text-primary mb-3">{group}</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {channels
                  .filter((c) => (c.group || 'Uncategorized') === group)
                  .map((ch) => (
                    <Card key={ch.id} hover>
                      <CardContent className="flex items-center gap-3 p-3">
                        {ch.logo_url ? (
                          <img src={ch.logo_url} alt="" className="w-10 h-10 rounded object-contain bg-bg-elevated" />
                        ) : (
                          <div className="w-10 h-10 rounded bg-bg-elevated flex items-center justify-center">
                            <Radio size={16} className="text-text-muted" />
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-body font-medium truncate">{ch.name}</p>
                          <p className="text-caption text-text-muted">
                            {ch.channel_number && `Ch. ${ch.channel_number}`}
                          </p>
                        </div>
                        <Badge variant={ch.enabled ? 'healthy' : 'default'}>
                          {ch.enabled ? 'On' : 'Off'}
                        </Badge>
                      </CardContent>
                    </Card>
                  ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
