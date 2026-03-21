import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { MediaCard } from '@/components/shared/MediaCard'
import { MediaCardSkeleton } from '@/components/shared/LoadingSkeleton'
import { EmptyState } from '@/components/shared/EmptyState'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import api from '@/lib/api'

interface TMDBResult {
  tmdb_id: number
  title: string
  year: number | null
  poster_url: string | null
  rating: number | null
  media_type: string
  overview: string | null
}

export function DiscoverPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [results, setResults] = useState<TMDBResult[]>([])
  const [trending, setTrending] = useState<TMDBResult[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchTrending = async () => {
      try {
        const { data } = await api.get('/discover/trending')
        setTrending(data)
      } catch {
        // TMDB not configured
      }
    }
    fetchTrending()
  }, [])

  useEffect(() => {
    const q = searchParams.get('q')
    if (q) {
      searchTMDB(q)
    }
  }, [searchParams])

  const searchTMDB = async (q: string) => {
    if (!q.trim()) return
    setLoading(true)
    try {
      const { data } = await api.get('/discover/search', { params: { q } })
      setResults(data)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      setSearchParams({ q: query })
    }
  }

  const handleRequest = async (item: TMDBResult) => {
    try {
      await api.post('/requests', {
        type: item.media_type === 'tv' ? 'series' : 'movie',
        tmdb_id: item.tmdb_id,
        title: item.title,
        year: item.year,
        poster_url: item.poster_url,
      })
      alert(`Requested: ${item.title}`)
    } catch {
      alert('Request failed')
    }
  }

  const displayItems = results.length > 0 ? results : trending

  return (
    <div>
      <PageHeader title="Discover" subtitle="Browse and request movies & TV shows" />

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6 max-w-lg">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <Input
            placeholder="Search movies and TV shows..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button type="submit">Search</Button>
      </form>

      {/* Results */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <MediaCardSkeleton key={i} />
          ))}
        </div>
      ) : displayItems.length > 0 ? (
        <>
          {results.length === 0 && (
            <h2 className="text-section-header text-text-primary mb-4">Trending</h2>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {displayItems.map((item) => (
              <MediaCard
                key={`${item.media_type}-${item.tmdb_id}`}
                title={item.title}
                year={item.year}
                posterUrl={item.poster_url}
                rating={item.rating}
                mediaType={item.media_type}
                onClick={() => handleRequest(item)}
              />
            ))}
          </div>
        </>
      ) : (
        <EmptyState
          icon={Search}
          title="No results found"
          description="Try a different search term or browse trending content."
        />
      )}
    </div>
  )
}
