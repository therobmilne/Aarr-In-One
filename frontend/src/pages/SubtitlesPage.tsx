import { useEffect, useState } from 'react'
import { Subtitles, Plus } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/shared/EmptyState'
import api from '@/lib/api'

interface SubtitleProfile {
  id: number
  name: string
  languages: string[]
  min_score: number
  providers: string[]
  hearing_impaired: boolean
  auto_download: boolean
  is_default: boolean
}

export function SubtitlesPage() {
  const [profiles, setProfiles] = useState<SubtitleProfile[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data } = await api.get('/subtitles/profiles')
        setProfiles(Array.isArray(data) ? data : [])
      } catch {
        // Not ready
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  return (
    <div>
      <PageHeader title="Subtitles" subtitle="Language profiles and providers">
        <Button><Plus size={16} className="mr-1" /> Add Profile</Button>
      </PageHeader>

      {profiles.length === 0 ? (
        <EmptyState
          icon={Subtitles}
          title="No subtitle profiles configured"
          description="Create a language profile to automatically download subtitles for your media."
          action={{ label: 'Create Profile', onClick: () => {} }}
        />
      ) : (
        <div className="space-y-3">
          {profiles.map((p) => (
            <Card key={p.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-body font-medium">{p.name}</span>
                      {p.is_default && <Badge variant="healthy">Default</Badge>}
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-caption text-text-muted">
                      <span>Languages: {p.languages.join(', ')}</span>
                      <span>Min Score: {p.min_score}%</span>
                      <span>Providers: {p.providers.join(', ')}</span>
                      {p.hearing_impaired && <span>HI</span>}
                      {p.auto_download && <Badge>Auto</Badge>}
                    </div>
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
