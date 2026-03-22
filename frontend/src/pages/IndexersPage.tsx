import { useEffect, useState } from 'react'
import { Globe, Plus, RefreshCw, Trash2, X } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/EmptyState'
import api from '@/lib/api'

interface ProwlarrIndexer {
  id: number
  name: string
  implementation: string
  protocol: string
  enable: boolean
  priority: number
  fields: { name: string; value: unknown }[]
  added?: string
}

export function IndexersPage() {
  const [indexers, setIndexers] = useState<ProwlarrIndexer[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [schemas, setSchemas] = useState<any[]>([])
  const [schemaSearch, setSchemaSearch] = useState('')
  const [testResults, setTestResults] = useState<Record<number, { success: boolean; message: string }>>({})

  const fetchIndexers = async () => {
    try {
      const { data } = await api.get('/indexers')
      setIndexers(Array.isArray(data) ? data : [])
    } catch { /* */ }
    finally { setLoading(false) }
  }

  const fetchSchemas = async () => {
    try {
      const { data } = await api.get('/indexers/schema')
      setSchemas(Array.isArray(data) ? data : [])
    } catch { /* */ }
  }

  useEffect(() => { fetchIndexers() }, [])

  const handleShowAdd = () => {
    if (schemas.length === 0) fetchSchemas()
    setShowAdd(!showAdd)
  }

  const addFromSchema = async (schema: any) => {
    // Open Prowlarr-style add dialog with the schema pre-filled
    // For now, add it directly with defaults
    try {
      await api.post('/indexers', schema)
      setShowAdd(false)
      fetchIndexers()
    } catch (e: any) {
      alert('Failed to add indexer: ' + (e.response?.data?.detail || e.message))
    }
  }

  const testIndexer = async (id: number) => {
    try {
      const { data } = await api.post(`/indexers/${id}/test`)
      setTestResults(prev => ({ ...prev, [id]: data }))
    } catch {
      setTestResults(prev => ({ ...prev, [id]: { success: false, message: 'Test failed' } }))
    }
  }

  const deleteIndexer = async (id: number) => {
    if (confirm('Remove this indexer?')) {
      await api.delete(`/indexers/${id}`)
      fetchIndexers()
    }
  }

  const getIndexerType = (idx: ProwlarrIndexer): string => {
    if (idx.protocol === 'usenet') return 'Usenet'
    if (idx.protocol === 'torrent') return 'Torrent'
    return idx.implementation || 'Unknown'
  }

  const filteredSchemas = schemas.filter((s) =>
    !schemaSearch || s.name?.toLowerCase().includes(schemaSearch.toLowerCase())
  )

  return (
    <div>
      <PageHeader title="Indexers" subtitle={`${indexers.length} configured (via Prowlarr)`}>
        <Button onClick={handleShowAdd}>
          <Plus size={16} className="mr-1" /> Add Indexer
        </Button>
      </PageHeader>

      {/* Add Indexer from Prowlarr schemas */}
      {showAdd && (
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-section-header">Add Indexer (Prowlarr)</span>
              <Button variant="ghost" size="icon" onClick={() => setShowAdd(false)}><X size={16} /></Button>
            </div>
            <Input
              placeholder="Search indexers..."
              value={schemaSearch}
              onChange={(e) => setSchemaSearch(e.target.value)}
              className="mb-4"
            />
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 max-h-64 overflow-y-auto">
              {filteredSchemas.slice(0, 50).map((schema, i) => (
                <button
                  key={schema.name || i}
                  onClick={() => addFromSchema(schema)}
                  className="text-left p-2 rounded-sm bg-bg-elevated hover:bg-bg-hover text-body transition-colors"
                >
                  <span className="font-medium text-sm">{schema.name}</span>
                  <Badge className="ml-2 text-xs">
                    {schema.protocol === 'usenet' ? 'Usenet' : 'Torrent'}
                  </Badge>
                </button>
              ))}
            </div>
            {filteredSchemas.length === 0 && schemas.length > 0 && (
              <p className="text-body text-text-muted">No indexers match "{schemaSearch}"</p>
            )}
            {schemas.length === 0 && (
              <p className="text-body text-text-muted">Loading indexer schemas from Prowlarr...</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Indexer List */}
      {indexers.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="No indexers configured"
          description="Add torrent or usenet indexers via Prowlarr. Indexers are automatically synced to Radarr and Sonarr."
          action={{ label: 'Add Indexer', onClick: handleShowAdd }}
        />
      ) : (
        <div className="space-y-2">
          {indexers.map((idx) => {
            const testResult = testResults[idx.id]
            return (
              <Card key={idx.id}>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <Globe size={18} className="text-text-muted shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-body font-medium">{idx.name}</span>
                        <Badge>{getIndexerType(idx)}</Badge>
                        <Badge variant={idx.enable ? 'healthy' : 'warning'}>
                          {idx.enable ? 'Enabled' : 'Disabled'}
                        </Badge>
                        {testResult && (
                          <Badge variant={testResult.success ? 'available' : 'failed'}>
                            {testResult.success ? 'Test OK' : 'Test Failed'}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-0.5 text-caption text-text-muted">
                        <span>Priority: {idx.priority}</span>
                        <span>{idx.implementation}</span>
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
            )
          })}
        </div>
      )}
    </div>
  )
}
