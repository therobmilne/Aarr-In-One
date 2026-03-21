import { useEffect, useState } from 'react'
import { Film, Plus } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { MediaCard } from '@/components/shared/MediaCard'
import { EmptyState } from '@/components/shared/EmptyState'
import { MediaCardSkeleton } from '@/components/shared/LoadingSkeleton'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import api from '@/lib/api'

interface Movie {
  id: number
  tmdb_id: number
  title: string
  year: number | null
  poster_url: string | null
  rating: number | null
  status: string
  quality: string | null
  resolution: string | null
  monitored: boolean
}

export function MoviesPage() {
  const [movies, setMovies] = useState<Movie[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const fetchMovies = async () => {
      try {
        const { data } = await api.get('/movies')
        setMovies(data)
      } catch {
        // Not ready
      } finally {
        setLoading(false)
      }
    }
    fetchMovies()
  }, [])

  if (loading) {
    return (
      <div>
        <PageHeader title="Movies" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => <MediaCardSkeleton key={i} />)}
        </div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Movies" subtitle={`${movies.length} movies`}>
        <Button onClick={() => navigate('/discover')}>
          <Plus size={16} className="mr-1" /> Add Movie
        </Button>
      </PageHeader>

      {movies.length === 0 ? (
        <EmptyState
          icon={Film}
          title="No movies in your library yet"
          description="Add your first movie by searching TMDB on the Discover page."
          action={{ label: 'Search Movies', onClick: () => navigate('/discover') }}
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {movies.map((movie) => (
            <MediaCard
              key={movie.id}
              title={movie.title}
              year={movie.year}
              posterUrl={movie.poster_url}
              rating={movie.rating}
              status={movie.status}
              quality={movie.resolution || movie.quality}
            />
          ))}
        </div>
      )}
    </div>
  )
}
