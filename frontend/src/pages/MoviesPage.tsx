import { useEffect, useState, useCallback, useRef } from 'react'
import { Film, Search, X, ChevronDown, Star, Check, Library, Compass, Download } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { MediaCard } from '@/components/shared/MediaCard'
import { EmptyState } from '@/components/shared/EmptyState'
import { MediaCardSkeleton } from '@/components/shared/LoadingSkeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import api from '@/lib/api'

// ── Types ──

interface TMDBMovie {
  id: number
  tmdb_id?: number
  title: string
  year?: number | null
  poster_url?: string | null
  backdrop_url?: string | null
  rating?: number | null
  overview?: string | null
  media_type?: string
}

interface LibraryMovie {
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

type View = 'browse' | 'library'
type LibraryFilter = 'all' | 'available' | 'missing' | 'downloading'
type Quality = 'any' | '720p' | '1080p' | '2160p'

const QUALITY_OPTIONS: { value: Quality; label: string }[] = [
  { value: 'any', label: 'Any' },
  { value: '720p', label: '720p' },
  { value: '1080p', label: '1080p' },
  { value: '2160p', label: '2160p / 4K' },
]

// ── Component ──

export function MoviesPage() {
  // View state
  const [view, setView] = useState<View>('browse')

  // Browse TMDB state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<TMDBMovie[]>([])
  const [trending, setTrending] = useState<TMDBMovie[]>([])
  const [popular, setPopular] = useState<TMDBMovie[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [browseLoading, setBrowseLoading] = useState(true)

  // Detail panel state
  const [selectedMovie, setSelectedMovie] = useState<TMDBMovie | null>(null)
  const [requestQuality, setRequestQuality] = useState<Quality>('1080p')
  const [requesting, setRequesting] = useState(false)
  const [requestSuccess, setRequestSuccess] = useState(false)
  const [showQualityForm, setShowQualityForm] = useState(false)

  // Library state
  const [libraryMovies, setLibraryMovies] = useState<LibraryMovie[]>([])
  const [libraryLoading, setLibraryLoading] = useState(false)
  const [libraryFilter, setLibraryFilter] = useState<LibraryFilter>('all')

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  // ── Fetch browse data ──

  useEffect(() => {
    if (view !== 'browse') return
    const fetchBrowse = async () => {
      setBrowseLoading(true)
      try {
        const [trendingRes, popularRes] = await Promise.all([
          api.get('/discover/trending', { params: { media_type: 'movie' } }),
          api.get('/discover/movies/popular'),
        ])
        setTrending(Array.isArray(trendingRes.data) ? trendingRes.data : trendingRes.data?.results || [])
        setPopular(Array.isArray(popularRes.data) ? popularRes.data : popularRes.data?.results || [])
      } catch {
        // silently handle
      } finally {
        setBrowseLoading(false)
      }
    }
    fetchBrowse()
  }, [view])

  // ── Fetch library data ──

  useEffect(() => {
    if (view !== 'library') return
    const fetchLibrary = async () => {
      setLibraryLoading(true)
      try {
        const { data } = await api.get('/movies')
        setLibraryMovies(Array.isArray(data) ? data : [])
      } catch {
        // silently handle
      } finally {
        setLibraryLoading(false)
      }
    }
    fetchLibrary()
  }, [view])

  // ── Debounced search ──

  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      setSearchLoading(false)
      return
    }
    setSearchLoading(true)
    try {
      const { data } = await api.get('/discover/search', { params: { q: query } })
      const results = Array.isArray(data) ? data : data?.results || []
      setSearchResults(results.filter((r: TMDBMovie) => !r.media_type || r.media_type === 'movie'))
    } catch {
      setSearchResults([])
    } finally {
      setSearchLoading(false)
    }
  }, [])

  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchQuery(value)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      if (!value.trim()) {
        setSearchResults([])
        setSearchLoading(false)
        return
      }
      setSearchLoading(true)
      debounceRef.current = setTimeout(() => performSearch(value), 500)
    },
    [performSearch]
  )

  // ── Select movie for detail ──

  const handleSelectMovie = useCallback((movie: TMDBMovie) => {
    setSelectedMovie(movie)
    setShowQualityForm(false)
    setRequestSuccess(false)
    setRequestQuality('1080p')
    setTimeout(() => detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }, [])

  const handleCloseDetail = useCallback(() => {
    setSelectedMovie(null)
    setShowQualityForm(false)
    setRequestSuccess(false)
  }, [])

  // ── Request download ──

  const handleConfirmRequest = useCallback(async () => {
    if (!selectedMovie) return
    setRequesting(true)
    try {
      await api.post('/requests', {
        type: 'movie',
        tmdb_id: selectedMovie.tmdb_id ?? selectedMovie.id,
        title: selectedMovie.title,
        year: selectedMovie.year,
        poster_url: selectedMovie.poster_url,
        quality: requestQuality,
      })
      setRequestSuccess(true)
      setShowQualityForm(false)
    } catch {
      // handle error silently
    } finally {
      setRequesting(false)
    }
  }, [selectedMovie, requestQuality])

  // ── Filter library ──

  const filteredLibrary = libraryMovies.filter((m) => {
    if (libraryFilter === 'all') return true
    return m.status === libraryFilter
  })

  // ── Helpers ──

  const isSearching = searchQuery.trim().length > 0

  const renderSkeletonRow = () => (
    <div className="flex gap-4 overflow-hidden">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="min-w-[150px]">
          <MediaCardSkeleton />
        </div>
      ))}
    </div>
  )

  const renderHorizontalRow = (title: string, movies: TMDBMovie[]) => (
    <div className="mb-lg">
      <h2 className="text-section-header text-text-primary mb-md">{title}</h2>
      <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
        {movies.map((movie) => (
          <div key={movie.id} className="min-w-[150px] max-w-[150px] flex-shrink-0">
            <MediaCard
              title={movie.title}
              year={movie.year}
              posterUrl={movie.poster_url}
              rating={movie.rating}
              onClick={() => handleSelectMovie(movie)}
            />
          </div>
        ))}
      </div>
    </div>
  )

  // ── Detail panel ──

  const renderDetailPanel = () => {
    if (!selectedMovie) return null
    return (
      <div ref={detailRef} className="mb-lg">
        <Card className="overflow-hidden">
          {/* Backdrop */}
          {selectedMovie.backdrop_url && (
            <div className="relative h-48 sm:h-64 md:h-72 overflow-hidden">
              <img
                src={selectedMovie.backdrop_url}
                alt=""
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-bg-surface via-bg-surface/60 to-transparent" />
            </div>
          )}

          <CardContent className={cn(selectedMovie.backdrop_url ? '-mt-24 relative z-10' : '')}>
            <div className="flex gap-md">
              {/* Poster */}
              <div className="flex-shrink-0 w-32 sm:w-40">
                {selectedMovie.poster_url ? (
                  <img
                    src={selectedMovie.poster_url}
                    alt={selectedMovie.title}
                    className="w-full rounded-md shadow-lg aspect-[2/3] object-cover"
                  />
                ) : (
                  <div className="w-full aspect-[2/3] rounded-md bg-bg-elevated flex items-center justify-center text-text-muted">
                    No Poster
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="text-page-title text-text-primary">{selectedMovie.title}</h2>
                    <div className="flex items-center gap-3 mt-1">
                      {selectedMovie.year && (
                        <span className="text-body text-text-secondary">{selectedMovie.year}</span>
                      )}
                      {selectedMovie.rating != null && selectedMovie.rating > 0 && (
                        <span className="flex items-center gap-1 text-body text-text-secondary">
                          <Star size={14} className="fill-status-warning text-status-warning" />
                          {selectedMovie.rating.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={handleCloseDetail}>
                    <X size={18} />
                  </Button>
                </div>

                {selectedMovie.overview && (
                  <p className="text-body text-text-secondary mt-md leading-relaxed line-clamp-4">
                    {selectedMovie.overview}
                  </p>
                )}

                {/* Actions */}
                <div className="mt-md flex flex-wrap items-center gap-3">
                  {requestSuccess ? (
                    <Badge variant="available">
                      <Check size={12} className="mr-1" />
                      Requested!
                    </Badge>
                  ) : showQualityForm ? (
                    <div className="flex items-center gap-2 flex-wrap">
                      <select
                        value={requestQuality}
                        onChange={(e) => setRequestQuality(e.target.value as Quality)}
                        className="h-10 rounded-sm border border-bg-elevated bg-bg-surface px-3 text-body text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
                      >
                        {QUALITY_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                      <Button onClick={handleConfirmRequest} disabled={requesting}>
                        {requesting ? 'Requesting...' : 'Confirm Request'}
                      </Button>
                      <Button variant="ghost" onClick={() => setShowQualityForm(false)}>
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button onClick={() => setShowQualityForm(true)}>
                      <Download size={16} className="mr-1" />
                      Request Download
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── Render ──

  return (
    <div>
      <PageHeader title="Movies" subtitle={view === 'library' ? `${filteredLibrary.length} movies` : 'Discover and manage movies'}>
        <div className="flex items-center gap-2">
          <Button
            variant={view === 'browse' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setView('browse')}
          >
            <Compass size={14} className="mr-1" />
            Browse TMDB
          </Button>
          <Button
            variant={view === 'library' ? 'default' : 'secondary'}
            size="sm"
            onClick={() => setView('library')}
          >
            <Library size={14} className="mr-1" />
            My Library
          </Button>
        </div>
      </PageHeader>

      {/* ── Browse TMDB View ── */}
      {view === 'browse' && (
        <div>
          {/* Search bar */}
          <div className="relative mb-lg">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <Input
              placeholder="Search movies on TMDB..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10 pr-10"
            />
            {searchQuery && (
              <button
                onClick={() => handleSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* Detail panel */}
          {renderDetailPanel()}

          {/* Search results or browse sections */}
          {isSearching ? (
            <div>
              <h2 className="text-section-header text-text-primary mb-md">
                {searchLoading ? 'Searching...' : `Results for "${searchQuery}"`}
              </h2>
              {searchLoading ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                  {Array.from({ length: 12 }).map((_, i) => (
                    <MediaCardSkeleton key={i} />
                  ))}
                </div>
              ) : searchResults.length === 0 ? (
                <EmptyState
                  icon={Search}
                  title="No results found"
                  description={`We couldn't find any movies matching "${searchQuery}". Try a different search term.`}
                />
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                  {searchResults.map((movie) => (
                    <MediaCard
                      key={movie.id}
                      title={movie.title}
                      year={movie.year}
                      posterUrl={movie.poster_url}
                      rating={movie.rating}
                      onClick={() => handleSelectMovie(movie)}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : browseLoading ? (
            <div>
              <h2 className="text-section-header text-text-primary mb-md">Trending Movies</h2>
              {renderSkeletonRow()}
              <h2 className="text-section-header text-text-primary mb-md mt-lg">Popular Movies</h2>
              {renderSkeletonRow()}
            </div>
          ) : (
            <div>
              {trending.length > 0 && renderHorizontalRow('Trending Movies', trending)}
              {popular.length > 0 && renderHorizontalRow('Popular Movies', popular)}
              {trending.length === 0 && popular.length === 0 && (
                <EmptyState
                  icon={Film}
                  title="Unable to load movies"
                  description="Could not fetch movies from TMDB. Please try again later."
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* ── My Library View ── */}
      {view === 'library' && (
        <div>
          {/* Filter buttons */}
          <div className="flex items-center gap-2 mb-lg flex-wrap">
            {(['all', 'available', 'missing', 'downloading'] as LibraryFilter[]).map((filter) => (
              <Button
                key={filter}
                variant={libraryFilter === filter ? 'default' : 'secondary'}
                size="sm"
                onClick={() => setLibraryFilter(filter)}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </Button>
            ))}
          </div>

          {libraryLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <MediaCardSkeleton key={i} />
              ))}
            </div>
          ) : filteredLibrary.length === 0 ? (
            <EmptyState
              icon={Film}
              title={libraryFilter === 'all' ? 'No movies in your library yet' : `No ${libraryFilter} movies`}
              description={
                libraryFilter === 'all'
                  ? 'Browse TMDB to discover and request movies.'
                  : `No movies with status "${libraryFilter}" found.`
              }
              action={
                libraryFilter === 'all'
                  ? { label: 'Browse TMDB', onClick: () => setView('browse') }
                  : { label: 'Show All', onClick: () => setLibraryFilter('all') }
              }
            />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {filteredLibrary.map((movie) => (
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
      )}
    </div>
  )
}
