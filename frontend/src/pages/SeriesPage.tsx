import { useEffect, useState } from 'react'
import { Tv, Plus } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { MediaCard } from '@/components/shared/MediaCard'
import { EmptyState } from '@/components/shared/EmptyState'
import { MediaCardSkeleton } from '@/components/shared/LoadingSkeleton'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import api from '@/lib/api'

interface Series {
  id: number
  title: string
  year: number | null
  poster_url: string | null
  rating: number | null
  status_text: string | null
  monitored: boolean
}

export function SeriesPage() {
  const [series, setSeries] = useState<Series[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchSeries = async () => {
      try {
        const { data } = await api.get('/series')
        setSeries(data)
      } catch {
        // Not ready
      } finally {
        setLoading(false)
      }
    }
    fetchSeries()
  }, [])

  if (loading) {
    return (
      <div>
        <PageHeader title="TV Shows" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => <MediaCardSkeleton key={i} />)}
        </div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="TV Shows" subtitle={`${series.length} series`}>
        <Button onClick={() => navigate('/discover')}>
          <Plus size={16} className="mr-1" /> Add Series
        </Button>
      </PageHeader>

      {series.length === 0 ? (
        <EmptyState
          icon={Tv}
          title="No TV shows in your library yet"
          description="Add your first series by searching on the Discover page."
          action={{ label: 'Search TV Shows', onClick: () => navigate('/discover') }}
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {series.map((s) => (
            <MediaCard
              key={s.id}
              title={s.title}
              year={s.year}
              posterUrl={s.poster_url}
              rating={s.rating}
              status={s.status_text || undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}
