import { useEffect, useState } from 'react'
import { Globe, Plus, RefreshCw, Trash2, Shield, X } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/EmptyState'
import api from '@/lib/api'

interface Indexer {
  id: number
  name: string
  type: string
  url: string
  enabled: boolean
  status: string
  priority: number
  average_response_ms: number
  total_queries: number
  total_grabs: number
  consecutive_failures: number
}

const INDEXER_PRESETS = [
  { category: 'Public Trackers', items: [
    { name: '1337x', type: 'torznab', url: 'https://1337x.to' },
    { name: 'RARBG (mirrors)', type: 'torznab', url: '' },
    { name: 'The Pirate Bay', type: 'torznab', url: 'https://thepiratebay.org' },
    { name: 'YTS', type: 'torznab', url: 'https://yts.mx' },
    { name: 'EZTV', type: 'torznab', url: 'https://eztv.re' },
    { name: 'Nyaa (Anime)', type: 'torznab', url: 'https://nyaa.si' },
    { name: 'TorrentGalaxy', type: 'torznab', url: 'https://torrentgalaxy.to' },
  ]},
  { category: 'Private Trackers', items: [
    { name: 'IPTorrents', type: 'torznab', url: '' },
    { name: 'TorrentLeech', type: 'torznab', url: '' },
    { name: 'FileList', type: 'torznab', url: '' },
    { name: 'BroadcasTheNet', type: 'torznab', url: '' },
    { name: 'PassThePopcorn', type: 'torznab', url: '' },
  ]},
  { category: 'Usenet Indexers', items: [
    { name: 'NZBgeek', type: 'newznab', url: 'https://api.nzbgeek.info' },
    { name: 'NZBFinder', type: 'newznab', url: 'https://nzbfinder.ws' },
    { name: 'DrunkenSlug', type: 'newznab', url: 'https://api.drunkenslug.com' },
    { name: 'NZBPlanet', type: 'newznab', url: 'https://api.nzbplanet.net' },
  ]},
  { category: 'Custom', items: [
    { name: 'Custom Torznab', type: 'torznab', url: '' },
    { name: 'Custom Newznab', type: 'newznab', url: '' },
  ]},
]

export function IndexersPage() {
  const [indexers, setIndexers] = useState<Indexer[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [addSearch, setAddSearch] = useState('')

  // Add form
  const [formName, setFormName] = useState('')
  const [formType, setFormType] = useState('torznab')
  const [formUrl, setFormUrl] = useState('')
  const [formApiKey, setFormApiKey] = useState('')
  const [formPriority, setFormPriority] = useState(25)
  const [formSaving, setFormSaving] = useState(false)

  const fetchIndexers = async () => {
    try {
      const { data } = await api.get('/indexers')
      setIndexers(Array.isArray(data) ? data : [])
    } catch { /* */ }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchIndexers() }, [])

  const selectPreset = (preset: { name: string; type: string; url: string }) => {
    setFormName(preset.name)
    setFormType(preset.type)
    setFormUrl(preset.url)
    setShowAdd(false)
  }

  const saveIndexer = async () => {
    setFormSaving(true)
    try {
      await api.post('/indexers', {
        name: formName,
        type: formType,
        url: formUrl,
        api_key: formApiKey || null,
        priority: formPriority,
      })
      setFormName('')
      setFormUrl('')
      setFormApiKey('')
      fetchIndexers()
    } catch { alert('Failed to save') }
    finally { setFormSaving(false) }
  }

  const testIndexer = async (id: number) => {
    try {
      const { data } = await api.post(`/indexers/${id}/test`)
      alert(data.success ? `OK (${Math.round(data.response_time_ms)}ms)` : `Failed: ${data.message}`)
      fetchIndexers()
    } catch { alert('Test failed') }
  }

  const deleteIndexer = async (id: number) => {
    if (confirm('Remove this indexer?')) {
      await api.delete(`/indexers/${id}`)
      fetchIndexers()
    }
  }

  const filteredPresets = INDEXER_PRESETS.map((cat) => ({
    ...cat,
    items: cat.items.filter((i) => !addSearch || i.name.toLowerCase().includes(addSearch.toLowerCase())),
  })).filter((cat) => cat.items.length > 0)

  return (
    <div>
      <PageHeader title="Indexers" subtitle={`${indexers.length} configured`}>
        <Button onClick={() => setShowAdd(!showAdd)}>
          <Plus size={16} className="mr-1" /> Add Indexer
        </Button>
      </PageHeader>

      {/* Add Indexer Picker */}
      {showAdd && (
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-section-header">Choose an Indexer</span>
              <Button variant="ghost" size="icon" onClick={() => setShowAdd(false)}><X size={16} /></Button>
            </div>
            <Input
              placeholder="Search indexers..."
              value={addSearch}
              onChange={(e) => setAddSearch(e.target.value)}
              className="mb-4"
            />
            <div className="space-y-4 max-h-64 overflow-y-auto">
              {filteredPresets.map((cat) => (
                <div key={cat.category}>
                  <p className="text-label text-text-muted uppercase mb-2">{cat.category}</p>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                    {cat.items.map((item) => (
                      <button
                        key={item.name}
                        onClick={() => selectPreset(item)}
                        className="text-left p-2 rounded-sm bg-bg-elevated hover:bg-bg-hover text-body transition-colors"
                      >
                        <span className="font-medium">{item.name}</span>
                        <Badge className="ml-2">{item.type === 'torznab' ? 'Torrent' : 'Usenet'}</Badge>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add/Edit Form */}
      {formName && (
        <Card className="mb-6">
          <CardContent className="p-4 space-y-3">
            <span className="text-section-header">Configure: {formName}</span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-label text-text-secondary mb-1">Name</label>
                <Input value={formName} onChange={(e) => setFormName(e.target.value)} />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">Type</label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  className="w-full h-10 rounded-sm border border-bg-elevated bg-bg-surface px-3 text-body text-text-primary"
                >
                  <option value="torznab">Torznab (Torrent)</option>
                  <option value="newznab">Newznab (Usenet)</option>
                </select>
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">URL</label>
                <Input value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="https://indexer.example.com" />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">API Key</label>
                <Input value={formApiKey} onChange={(e) => setFormApiKey(e.target.value)} placeholder="Optional" />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">Priority (1=highest)</label>
                <Input type="number" value={formPriority} onChange={(e) => setFormPriority(Number(e.target.value))} />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={saveIndexer} disabled={formSaving || !formUrl}>
                {formSaving ? 'Saving...' : 'Save Indexer'}
              </Button>
              <Button variant="ghost" onClick={() => { setFormName(''); setFormUrl(''); setFormApiKey('') }}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Indexer List */}
      {indexers.length === 0 && !formName ? (
        <EmptyState
          icon={Globe}
          title="No indexers configured"
          description="Add torrent or usenet indexers to search for content. Click 'Add Indexer' above to get started."
          action={{ label: 'Add Indexer', onClick: () => setShowAdd(true) }}
        />
      ) : (
        <div className="space-y-2">
          {indexers.map((idx) => (
            <Card key={idx.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <Globe size={18} className="text-text-muted shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-body font-medium">{idx.name}</span>
                      <Badge>{idx.type === 'torznab' ? 'Torrent' : 'Usenet'}</Badge>
                      <Badge variant={idx.status === 'healthy' ? 'healthy' : idx.status === 'failed' ? 'failed' : 'warning'}>
                        {idx.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 mt-0.5 text-caption text-text-muted">
                      <span>{Math.round(idx.average_response_ms)}ms</span>
                      <span>{idx.total_queries} queries</span>
                      <span>{idx.total_grabs} grabs</span>
                      <span>Priority: {idx.priority}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={() => testIndexer(idx.id)} title="Test">
                    <RefreshCw size={14} />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => deleteIndexer(idx.id)} title="Delete">
                    <Trash2 size={14} className="text-status-error" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
