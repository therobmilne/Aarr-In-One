import { useEffect, useState } from 'react'
import { Globe, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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

export function IndexersPage() {
  const [indexers, setIndexers] = useState<Indexer[]>([])
  const [loading, setLoading] = useState(true)

  const fetchIndexers = async () => {
    try {
      const { data } = await api.get('/indexers')
      setIndexers(data)
    } catch {
      // Not ready
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchIndexers() }, [])

  const testIndexer = async (id: number) => {
    try {
      const { data } = await api.post(`/indexers/${id}/test`)
      alert(data.success ? `OK (${Math.round(data.response_time_ms)}ms)` : `Failed: ${data.message}`)
      fetchIndexers()
    } catch {
      alert('Test failed')
    }
  }

  const deleteIndexer = async (id: number) => {
    if (confirm('Remove this indexer?')) {
      await api.delete(`/indexers/${id}`)
      fetchIndexers()
    }
  }

  return (
    <div>
      <PageHeader title="Indexers" subtitle={`${indexers.length} configured`}>
        <Button><Plus size={16} className="mr-1" /> Add Indexer</Button>
      </PageHeader>

      {indexers.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="No indexers configured"
          description="Add torrent or usenet indexers to search for content."
          action={{ label: 'Add Indexer', onClick: () => {} }}
        />
      ) : (
        <div className="space-y-3">
          {indexers.map((idx) => (
            <Card key={idx.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <Globe size={18} className="text-text-muted" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-body font-medium">{idx.name}</span>
                      <Badge>{idx.type}</Badge>
                      <Badge variant={idx.status === 'healthy' ? 'healthy' : idx.status === 'failed' ? 'failed' : 'warning'}>
                        {idx.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 mt-0.5 text-caption text-text-muted">
                      <span>{Math.round(idx.average_response_ms)}ms avg</span>
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
