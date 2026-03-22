import { useEffect, useState } from 'react'
import { Radio, Search, Copy, Check, RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/EmptyState'
import api from '@/lib/api'

interface Channel {
  id: number
  name: string
  channel_number: number | null
  group: string | null
  logo_url: string | null
  enabled: boolean
}

type Tab = 'groups' | 'channels' | 'epg' | 'output'

export function LiveTVPage() {
  const [channels, setChannels] = useState<Channel[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('groups')
  const [search, setSearch] = useState('')
  const [copied, setCopied] = useState('')

  const fetchChannels = async () => {
    try {
      const { data } = await api.get('/livetv/channels')
      setChannels(Array.isArray(data) ? data : [])
    } catch { /* */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchChannels() }, [])

  const groups = [...new Set(channels.map((c) => c.group || 'Uncategorized'))].sort()
  const groupCounts = groups.map((g) => ({
    name: g,
    total: channels.filter((c) => (c.group || 'Uncategorized') === g).length,
    enabled: channels.filter((c) => (c.group || 'Uncategorized') === g && c.enabled).length,
  }))

  const filteredChannels = channels.filter((c) =>
    !search || c.name.toLowerCase().includes(search.toLowerCase())
  )

  const toggleGroup = async (group: string, enable: boolean) => {
    const groupCh = channels.filter((c) => (c.group || 'Uncategorized') === group)
    for (const ch of groupCh) {
      try { await api.put(`/livetv/channels/${ch.id}`, { enabled: enable }) } catch { /* */ }
    }
    fetchChannels()
  }

  const toggleChannel = async (id: number, enabled: boolean) => {
    try {
      await api.put(`/livetv/channels/${id}`, { enabled })
      setChannels((prev) => prev.map((c) => c.id === id ? { ...c, enabled } : c))
    } catch { /* */ }
  }

  const copyUrl = (url: string, label: string) => {
    navigator.clipboard.writeText(url)
    setCopied(label)
    setTimeout(() => setCopied(''), 2000)
  }

  const baseUrl = window.location.origin

  if (!loading && channels.length === 0) {
    return (
      <div>
        <PageHeader title="Live TV" />
        <EmptyState
          icon={Radio}
          title="No IPTV channels found"
          description="Add your IPTV credentials in Settings and run a scan to discover live TV channels."
          action={{ label: 'Go to Settings', onClick: () => { window.location.href = '/settings' } }}
        />
      </div>
    )
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'groups', label: 'Groups' },
    { id: 'channels', label: `Channels (${channels.filter((c) => c.enabled).length}/${channels.length})` },
    { id: 'epg', label: 'EPG' },
    { id: 'output', label: 'Jellyfin URLs' },
  ]

  return (
    <div>
      <PageHeader title="Live TV" subtitle={`${channels.filter((c) => c.enabled).length} of ${channels.length} channels enabled`} />

      <div className="flex gap-1 mb-6 border-b border-bg-elevated overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-body whitespace-nowrap transition-colors border-b-2 ${
              activeTab === tab.id ? 'text-accent-primary border-accent-primary' : 'text-text-secondary border-transparent hover:text-text-primary'
            }`}
          >{tab.label}</button>
        ))}
      </div>

      {activeTab === 'groups' && (
        <div className="space-y-2">
          {groupCounts.map((g) => (
            <Card key={g.name}>
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <span className="text-body font-medium">{g.name}</span>
                  <span className="text-caption text-text-muted ml-3">{g.enabled}/{g.total} enabled</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="secondary" size="sm" onClick={() => toggleGroup(g.name, true)}>Enable All</Button>
                  <Button variant="ghost" size="sm" onClick={() => toggleGroup(g.name, false)}>Disable All</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'channels' && (
        <div>
          <div className="relative max-w-sm mb-4">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <Input placeholder="Search channels..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
          <div className="space-y-1">
            {filteredChannels.map((ch) => (
              <div key={ch.id} className="flex items-center gap-3 p-3 bg-bg-surface rounded-sm border border-bg-elevated">
                {ch.logo_url ? (
                  <img src={ch.logo_url} alt="" className="w-8 h-8 rounded object-contain bg-bg-elevated" />
                ) : (
                  <div className="w-8 h-8 rounded bg-bg-elevated flex items-center justify-center">
                    <Radio size={12} className="text-text-muted" />
                  </div>
                )}
                <span className="text-caption text-text-muted w-10">{ch.channel_number || '--'}</span>
                <span className="text-body flex-1 truncate">{ch.name}</span>
                <Badge>{ch.group || 'Other'}</Badge>
                <input
                  type="checkbox"
                  checked={ch.enabled}
                  onChange={(e) => toggleChannel(ch.id, e.target.checked)}
                  className="w-4 h-4 rounded accent-accent-primary cursor-pointer"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'epg' && (
        <Card>
          <CardHeader><CardTitle>Electronic Program Guide</CardTitle></CardHeader>
          <CardContent>
            <p className="text-body text-text-secondary mb-4">EPG data is refreshed automatically from your IPTV provider.</p>
            <Button variant="secondary"><RefreshCw size={14} className="mr-1" /> Refresh EPG Now</Button>
          </CardContent>
        </Card>
      )}

      {activeTab === 'output' && (
        <div className="space-y-4 max-w-2xl">
          <p className="text-body text-text-secondary">Copy these URLs into Jellyfin under Settings &gt; Live TV.</p>
          {[
            { label: 'M3U Playlist', url: `${baseUrl}/api/v1/livetv/output/m3u`, desc: 'Add as M3U Tuner in Jellyfin' },
            { label: 'XMLTV EPG', url: `${baseUrl}/api/v1/livetv/epg.xml`, desc: 'Add as TV Guide Provider in Jellyfin' },
            { label: 'HDHomeRun Tuner', url: `${baseUrl}/discover.json`, desc: 'Add as HD HomeRun tuner in Jellyfin' },
          ].map((item) => (
            <Card key={item.label}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-body font-medium">{item.label}</span>
                  <Button variant="secondary" size="sm" onClick={() => copyUrl(item.url, item.label)}>
                    {copied === item.label ? <><Check size={12} className="mr-1" /> Copied!</> : <><Copy size={12} className="mr-1" /> Copy</>}
                  </Button>
                </div>
                <code className="text-caption text-accent-primary break-all">{item.url}</code>
                <p className="text-caption text-text-muted mt-1">{item.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
