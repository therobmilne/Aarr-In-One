import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Tv,
  Search,
  X,
  ChevronDown,
  ChevronRight,
  Star,
  Calendar,
  Monitor,
  Loader2,
  Library,
  TrendingUp,
  Flame,
  Check,
} from 'lucide-react'
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DiscoverShow {
  id: number
  title: string
  year: number | null
  poster_url: string | null
  backdrop_url?: string | null
  rating: number | null
  overview?: string | null
  network?: string | null
  tmdb_id?: number
  first_air_date?: string | null
  genres?: string[]
}

interface Season {
  season_number: number
  episode_count: number
  name?: string
}

interface SeriesDetail extends DiscoverShow {
  seasons: Season[]
}

interface LibrarySeries {
  id: number
  title: string
  year: number | null
  poster_url: string | null
  rating: number | null
  status_text: string | null
  monitored: boolean
  tmdb_id?: number
}

interface Episode {
  episode_number: number
  title: string
  air_date: string | null
  status: string | null
  quality: string | null
  overview?: string | null
}

type ViewMode = 'browse' | 'library'
type LibraryFilter = 'all' | 'available' | 'missing'
type SeasonChoice = 'all' | 'latest' | 'select'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

function statusVariant(status: string | null | undefined) {
  if (!status) return 'default' as const
  const s = status.toLowerCase()
  if (s.includes('available') || s.includes('downloaded')) return 'available' as const
  if (s.includes('download') || s.includes('importing')) return 'downloading' as const
  if (s.includes('missing')) return 'error' as const
  return 'pending' as const
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SeriesPage() {
  // View toggle
  const [view, setView] = useState<ViewMode>('browse')

  // Browse state
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedQuery = useDebounce(searchQuery, 400)
  const [searchResults, setSearchResults] = useState<DiscoverShow[]>([])
  const [trending, setTrending] = useState<DiscoverShow[]>([])
  const [popular, setPopular] = useState<DiscoverShow[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [browseLoading, setBrowseLoading] = useState(true)

  // Detail panel (browse)
  const [selectedShow, setSelectedShow] = useState<DiscoverShow | null>(null)
  const [showDetail, setShowDetail] = useState<SeriesDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // Request form
  const [requestOpen, setRequestOpen] = useState(false)
  const [qualityChoice, setQualityChoice] = useState('any')
  const [seasonChoice, setSeasonChoice] = useState<SeasonChoice>('all')
  const [selectedSeasons, setSelectedSeasons] = useState<number[]>([])
  const [requesting, setRequesting] = useState(false)
  const [requestSuccess, setRequestSuccess] = useState(false)

  // Library state
  const [library, setLibrary] = useState<LibrarySeries[]>([])
  const [libraryLoading, setLibraryLoading] = useState(false)
  const [libraryFilter, setLibraryFilter] = useState<LibraryFilter>('all')

  // Library drill-down
  const [selectedLibSeries, setSelectedLibSeries] = useState<LibrarySeries | null>(null)
  const [libSeriesDetail, setLibSeriesDetail] = useState<SeriesDetail | null>(null)
  const [libDetailLoading, setLibDetailLoading] = useState(false)
  const [expandedSeasons, setExpandedSeasons] = useState<Record<number, boolean>>({})
  const [seasonEpisodes, setSeasonEpisodes] = useState<Record<number, Episode[]>>({})
  const [episodesLoading, setEpisodesLoading] = useState<Record<number, boolean>>({})

  const detailRef = useRef<HTMLDivElement>(null)

  // -------------------------------------------------------------------------
  // Data fetching
  // -------------------------------------------------------------------------

  // Trending + Popular on mount
  useEffect(() => {
    if (view !== 'browse') return
    let cancelled = false
    const fetchBrowse = async () => {
      setBrowseLoading(true)
      try {
        const [trendRes, popRes] = await Promise.all([
          api.get('/discover/trending', { params: { media_type: 'tv' } }),
          api.get('/discover/tv/popular'),
        ])
        if (!cancelled) {
          setTrending(Array.isArray(trendRes.data) ? trendRes.data : trendRes.data?.results || [])
          setPopular(Array.isArray(popRes.data) ? popRes.data : popRes.data?.results || [])
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setBrowseLoading(false)
      }
    }
    fetchBrowse()
    return () => { cancelled = true }
  }, [view])

  // Search
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setSearchResults([])
      return
    }
    let cancelled = false
    const doSearch = async () => {
      setSearchLoading(true)
      try {
        const { data } = await api.get('/discover/search', { params: { q: debouncedQuery } })
        if (!cancelled) {
          const results = Array.isArray(data) ? data : data?.results || []
          setSearchResults(results.filter((r: any) => r.media_type === 'tv' || !r.media_type))
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setSearchLoading(false)
      }
    }
    doSearch()
    return () => { cancelled = true }
  }, [debouncedQuery])

  // Library
  useEffect(() => {
    if (view !== 'library') return
    let cancelled = false
    const fetchLib = async () => {
      setLibraryLoading(true)
      try {
        const { data } = await api.get('/series')
        if (!cancelled) setLibrary(Array.isArray(data) ? data : [])
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLibraryLoading(false)
      }
    }
    fetchLib()
    return () => { cancelled = true }
  }, [view])

  // -------------------------------------------------------------------------
  // Browse detail
  // -------------------------------------------------------------------------

  const openDetail = useCallback(async (show: DiscoverShow) => {
    setSelectedShow(show)
    setShowDetail(null)
    setRequestOpen(false)
    setRequestSuccess(false)
    setDetailLoading(true)

    const tmdbId = show.tmdb_id || show.id
    try {
      const { data } = await api.get(`/series/${tmdbId}`)
      setShowDetail(data)
    } catch {
      // Fall back with empty seasons
      setShowDetail({ ...show, seasons: [] })
    } finally {
      setDetailLoading(false)
    }

    setTimeout(() => detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
  }, [])

  const closeDetail = useCallback(() => {
    setSelectedShow(null)
    setShowDetail(null)
    setRequestOpen(false)
    setRequestSuccess(false)
  }, [])

  // -------------------------------------------------------------------------
  // Request
  // -------------------------------------------------------------------------

  const handleRequest = useCallback(async () => {
    if (!selectedShow) return
    setRequesting(true)
    try {
      let requestedSeasons: number[] | undefined
      if (seasonChoice === 'select') {
        requestedSeasons = selectedSeasons
      } else if (seasonChoice === 'latest' && showDetail?.seasons?.length) {
        const realSeasons = showDetail.seasons.filter(s => s.season_number > 0)
        const last = realSeasons[realSeasons.length - 1]
        requestedSeasons = last ? [last.season_number] : undefined
      }

      await api.post('/requests', {
        type: 'series',
        tmdb_id: selectedShow.tmdb_id || selectedShow.id,
        title: selectedShow.title,
        year: selectedShow.year,
        poster_url: selectedShow.poster_url,
        quality: qualityChoice === 'any' ? undefined : qualityChoice,
        requested_seasons: requestedSeasons,
      })
      setRequestSuccess(true)
    } catch {
      // ignore
    } finally {
      setRequesting(false)
    }
  }, [selectedShow, showDetail, seasonChoice, selectedSeasons, qualityChoice])

  // -------------------------------------------------------------------------
  // Library drill-down
  // -------------------------------------------------------------------------

  const openLibDetail = useCallback(async (series: LibrarySeries) => {
    setSelectedLibSeries(series)
    setLibSeriesDetail(null)
    setExpandedSeasons({})
    setSeasonEpisodes({})
    setLibDetailLoading(true)
    try {
      const { data } = await api.get(`/series/${series.id}`)
      setLibSeriesDetail(data)
    } catch {
      setLibSeriesDetail(null)
    } finally {
      setLibDetailLoading(false)
    }
  }, [])

  const closeLibDetail = useCallback(() => {
    setSelectedLibSeries(null)
    setLibSeriesDetail(null)
  }, [])

  const toggleSeason = useCallback(async (seriesId: number, seasonNum: number) => {
    setExpandedSeasons(prev => {
      const next = { ...prev }
      next[seasonNum] = !next[seasonNum]
      return next
    })

    if (seasonEpisodes[seasonNum]) return

    setEpisodesLoading(prev => ({ ...prev, [seasonNum]: true }))
    try {
      const { data } = await api.get(`/series/${seriesId}/episodes`, { params: { season: seasonNum } })
      setSeasonEpisodes(prev => ({ ...prev, [seasonNum]: Array.isArray(data) ? data : data?.episodes || [] }))
    } catch {
      setSeasonEpisodes(prev => ({ ...prev, [seasonNum]: [] }))
    } finally {
      setEpisodesLoading(prev => ({ ...prev, [seasonNum]: false }))
    }
  }, [seasonEpisodes])

  const handleSearchSeason = useCallback(async (seriesId: number, seasonNum: number) => {
    try {
      await api.post(`/series/${seriesId}/search`, { season: seasonNum })
    } catch {
      // ignore
    }
  }, [])

  // -------------------------------------------------------------------------
  // Filtered library
  // -------------------------------------------------------------------------

  const filteredLibrary = library.filter(s => {
    if (libraryFilter === 'all') return true
    const st = (s.status_text || '').toLowerCase()
    if (libraryFilter === 'available') return st.includes('available') || st.includes('completed') || st.includes('downloaded')
    if (libraryFilter === 'missing') return st.includes('missing') || st === '' || !s.status_text
    return true
  })

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------

  const renderHorizontalRow = (title: string, icon: React.ReactNode, items: DiscoverShow[]) => (
    <div className="mb-lg">
      <div className="flex items-center gap-2 mb-md">
        {icon}
        <h2 className="text-section-header text-text-primary">{title}</h2>
      </div>
      <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
        {items.map(item => (
          <div key={item.id} className="flex-shrink-0 w-[150px]">
            <MediaCard
              title={item.title}
              year={item.year}
              posterUrl={item.poster_url}
              rating={item.rating}
              mediaType="tv"
              onClick={() => openDetail(item)}
            />
          </div>
        ))}
      </div>
    </div>
  )

  const renderDetailPanel = () => {
    if (!selectedShow) return null
    const show = showDetail || selectedShow
    const backdropUrl = show.backdrop_url
      ? show.backdrop_url
      : show.poster_url
    const seasons = showDetail?.seasons?.filter(s => s.season_number > 0) || []

    return (
      <div ref={detailRef} className="mb-lg">
        <Card>
          {/* Backdrop */}
          <div className="relative h-48 md:h-64 overflow-hidden rounded-t-md">
            {backdropUrl ? (
              <img src={backdropUrl} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full bg-bg-elevated" />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-bg-surface via-bg-surface/60 to-transparent" />
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-3 right-3 bg-bg-surface/60 hover:bg-bg-surface"
              onClick={closeDetail}
            >
              <X size={18} />
            </Button>
          </div>

          <CardContent className="-mt-20 relative z-10">
            <div className="flex gap-6">
              {/* Poster */}
              <div className="flex-shrink-0 w-32 md:w-40">
                <div className="aspect-[2/3] rounded-md overflow-hidden shadow-lg bg-bg-elevated">
                  {show.poster_url ? (
                    <img src={show.poster_url} alt={show.title} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-text-muted">No Poster</div>
                  )}
                </div>
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0 pt-16 md:pt-12">
                <h2 className="text-page-title text-text-primary mb-1">{show.title}</h2>
                <div className="flex flex-wrap items-center gap-3 mb-3 text-body text-text-secondary">
                  {show.year && (
                    <span className="flex items-center gap-1">
                      <Calendar size={14} />
                      {show.year}
                    </span>
                  )}
                  {show.rating != null && show.rating > 0 && (
                    <span className="flex items-center gap-1">
                      <Star size={14} className="fill-status-warning text-status-warning" />
                      {show.rating.toFixed(1)}
                    </span>
                  )}
                  {show.network && (
                    <span className="flex items-center gap-1">
                      <Monitor size={14} />
                      {show.network}
                    </span>
                  )}
                </div>

                {show.overview && (
                  <p className="text-body text-text-secondary mb-4 line-clamp-4">{show.overview}</p>
                )}

                {detailLoading ? (
                  <div className="flex items-center gap-2 text-text-muted">
                    <Loader2 size={16} className="animate-spin" />
                    Loading details...
                  </div>
                ) : requestSuccess ? (
                  <div className="flex items-center gap-2 text-status-success">
                    <Check size={18} />
                    <span className="text-body font-medium">Request submitted successfully!</span>
                  </div>
                ) : !requestOpen ? (
                  <div className="flex gap-2">
                    <Button onClick={() => setRequestOpen(true)}>Request</Button>
                    <Button variant="ghost" onClick={closeDetail}>Close</Button>
                  </div>
                ) : (
                  /* Request form */
                  <div className="space-y-4 max-w-md">
                    {/* Quality */}
                    <div>
                      <label className="text-caption text-text-secondary block mb-1">Quality</label>
                      <select
                        value={qualityChoice}
                        onChange={e => setQualityChoice(e.target.value)}
                        className="flex h-10 w-full rounded-sm border border-bg-elevated bg-bg-surface px-3 py-2 text-body text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
                      >
                        <option value="any">Any</option>
                        <option value="720p">720p</option>
                        <option value="1080p">1080p</option>
                        <option value="2160p">2160p / 4K</option>
                      </select>
                    </div>

                    {/* Season choice */}
                    <div>
                      <label className="text-caption text-text-secondary block mb-2">What to download</label>
                      <div className="space-y-2">
                        {(['all', 'latest', 'select'] as SeasonChoice[]).map(opt => (
                          <label key={opt} className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="radio"
                              name="seasonChoice"
                              checked={seasonChoice === opt}
                              onChange={() => {
                                setSeasonChoice(opt)
                                if (opt !== 'select') setSelectedSeasons([])
                              }}
                              className="accent-accent-primary"
                            />
                            <span className="text-body text-text-primary">
                              {opt === 'all' && 'All Seasons'}
                              {opt === 'latest' && 'Latest Season Only'}
                              {opt === 'select' && 'Select Seasons...'}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Season checkboxes */}
                    {seasonChoice === 'select' && seasons.length > 0 && (
                      <div className="pl-6 space-y-1">
                        {seasons.map(s => (
                          <label key={s.season_number} className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={selectedSeasons.includes(s.season_number)}
                              onChange={e => {
                                if (e.target.checked) {
                                  setSelectedSeasons(prev => [...prev, s.season_number])
                                } else {
                                  setSelectedSeasons(prev => prev.filter(n => n !== s.season_number))
                                }
                              }}
                              className="accent-accent-primary"
                            />
                            <span className="text-body text-text-primary">
                              {s.name || `Season ${s.season_number}`}
                              <span className="text-text-muted ml-1">({s.episode_count} episodes)</span>
                            </span>
                          </label>
                        ))}
                      </div>
                    )}

                    {seasonChoice === 'select' && seasons.length === 0 && (
                      <p className="pl-6 text-caption text-text-muted">No season information available.</p>
                    )}

                    <div className="flex gap-2">
                      <Button
                        onClick={handleRequest}
                        disabled={requesting || (seasonChoice === 'select' && selectedSeasons.length === 0)}
                      >
                        {requesting ? (
                          <>
                            <Loader2 size={14} className="animate-spin mr-1" />
                            Requesting...
                          </>
                        ) : (
                          'Confirm Request'
                        )}
                      </Button>
                      <Button variant="ghost" onClick={() => setRequestOpen(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // Library detail panel
  // -------------------------------------------------------------------------

  const renderLibraryDetail = () => {
    if (!selectedLibSeries) return null

    return (
      <div className="mb-lg">
        <Card>
          <CardContent>
            <div className="flex items-start justify-between mb-md">
              <div className="flex items-center gap-4">
                {selectedLibSeries.poster_url && (
                  <img
                    src={selectedLibSeries.poster_url}
                    alt={selectedLibSeries.title}
                    className="w-16 h-24 object-cover rounded-sm"
                  />
                )}
                <div>
                  <h2 className="text-section-header text-text-primary">{selectedLibSeries.title}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    {selectedLibSeries.year && (
                      <span className="text-caption text-text-muted">{selectedLibSeries.year}</span>
                    )}
                    {selectedLibSeries.status_text && (
                      <Badge variant={statusVariant(selectedLibSeries.status_text)}>
                        {selectedLibSeries.status_text}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={closeLibDetail}>
                <X size={18} />
              </Button>
            </div>

            {libDetailLoading ? (
              <div className="flex items-center gap-2 text-text-muted py-4">
                <Loader2 size={16} className="animate-spin" />
                Loading seasons...
              </div>
            ) : !libSeriesDetail?.seasons?.length ? (
              <p className="text-body text-text-muted py-4">No season information available.</p>
            ) : (
              <div className="space-y-1">
                {libSeriesDetail.seasons
                  .filter(s => s.season_number > 0)
                  .map(season => {
                    const isExpanded = expandedSeasons[season.season_number]
                    const episodes = seasonEpisodes[season.season_number]
                    const loading = episodesLoading[season.season_number]

                    return (
                      <div key={season.season_number} className="border border-bg-elevated rounded-sm overflow-hidden">
                        {/* Season header */}
                        <button
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-bg-hover transition-colors text-left"
                          onClick={() => toggleSeason(selectedLibSeries.id, season.season_number)}
                        >
                          <div className="flex items-center gap-2">
                            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                            <span className="text-body font-medium text-text-primary">
                              {season.name || `Season ${season.season_number}`}
                            </span>
                            <span className="text-caption text-text-muted">
                              {season.episode_count} episodes
                            </span>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={e => {
                              e.stopPropagation()
                              handleSearchSeason(selectedLibSeries.id, season.season_number)
                            }}
                          >
                            <Search size={12} className="mr-1" />
                            Search Season
                          </Button>
                        </button>

                        {/* Episodes */}
                        {isExpanded && (
                          <div className="border-t border-bg-elevated">
                            {loading ? (
                              <div className="flex items-center gap-2 text-text-muted px-4 py-3">
                                <Loader2 size={14} className="animate-spin" />
                                Loading episodes...
                              </div>
                            ) : !episodes?.length ? (
                              <p className="text-caption text-text-muted px-4 py-3">No episodes found.</p>
                            ) : (
                              <div className="divide-y divide-bg-elevated">
                                {episodes.map(ep => (
                                  <div
                                    key={ep.episode_number}
                                    className="flex items-center gap-4 px-4 py-2.5 text-body hover:bg-bg-hover/50"
                                  >
                                    <span className="text-text-muted w-8 text-center font-mono text-caption">
                                      {ep.episode_number}
                                    </span>
                                    <span className="flex-1 text-text-primary truncate min-w-0">
                                      {ep.title || `Episode ${ep.episode_number}`}
                                    </span>
                                    {ep.air_date && (
                                      <span className="text-caption text-text-muted flex-shrink-0">
                                        {ep.air_date}
                                      </span>
                                    )}
                                    {ep.quality && (
                                      <Badge variant={ep.quality.includes('4K') || ep.quality.includes('2160') ? 'warning' : 'default'}>
                                        {ep.quality}
                                      </Badge>
                                    )}
                                    <Badge variant={statusVariant(ep.status)}>
                                      {ep.status || 'Unknown'}
                                    </Badge>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // Main render
  // -------------------------------------------------------------------------

  return (
    <div>
      <PageHeader title="TV Shows" subtitle={view === 'library' ? `${filteredLibrary.length} series` : undefined}>
        <div className="flex items-center gap-1 bg-bg-elevated rounded-sm p-0.5">
          <Button
            size="sm"
            variant={view === 'browse' ? 'default' : 'ghost'}
            onClick={() => { setView('browse'); closeLibDetail() }}
          >
            <TrendingUp size={14} className="mr-1" />
            Browse TMDB
          </Button>
          <Button
            size="sm"
            variant={view === 'library' ? 'default' : 'ghost'}
            onClick={() => { setView('library'); closeDetail() }}
          >
            <Library size={14} className="mr-1" />
            My Library
          </Button>
        </div>
      </PageHeader>

      {/* ================================================================= */}
      {/* BROWSE VIEW                                                        */}
      {/* ================================================================= */}
      {view === 'browse' && (
        <div>
          {/* Search bar */}
          <div className="relative mb-lg">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <Input
              placeholder="Search TV shows on TMDB..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-10 pr-10"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* Detail panel */}
          {renderDetailPanel()}

          {/* Search results or browse rows */}
          {debouncedQuery.trim() ? (
            <div>
              <h2 className="text-section-header text-text-primary mb-md">
                Search Results {searchResults.length > 0 && `(${searchResults.length})`}
              </h2>
              {searchLoading ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                  {Array.from({ length: 12 }).map((_, i) => <MediaCardSkeleton key={i} />)}
                </div>
              ) : searchResults.length === 0 ? (
                <EmptyState
                  icon={Search}
                  title="No results found"
                  description={`No TV shows found matching "${debouncedQuery}". Try a different search term.`}
                />
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                  {searchResults.map(show => (
                    <MediaCard
                      key={show.id}
                      title={show.title}
                      year={show.year}
                      posterUrl={show.poster_url}
                      rating={show.rating}
                      mediaType="tv"
                      onClick={() => openDetail(show)}
                      className={cn(
                        selectedShow?.id === show.id && 'ring-2 ring-accent-primary rounded-md'
                      )}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : browseLoading ? (
            <div>
              <div className="mb-lg">
                <div className="h-6 w-48 bg-bg-elevated rounded mb-md" />
                <div className="flex gap-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex-shrink-0 w-[150px]">
                      <MediaCardSkeleton />
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="h-6 w-48 bg-bg-elevated rounded mb-md" />
                <div className="flex gap-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="flex-shrink-0 w-[150px]">
                      <MediaCardSkeleton />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div>
              {trending.length > 0 && renderHorizontalRow(
                'Trending TV Shows',
                <TrendingUp size={20} className="text-accent-primary" />,
                trending
              )}
              {popular.length > 0 && renderHorizontalRow(
                'Popular TV Shows',
                <Flame size={20} className="text-status-warning" />,
                popular
              )}
              {trending.length === 0 && popular.length === 0 && (
                <EmptyState
                  icon={Tv}
                  title="No shows available"
                  description="Unable to load trending and popular shows. Try searching instead."
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* ================================================================= */}
      {/* LIBRARY VIEW                                                       */}
      {/* ================================================================= */}
      {view === 'library' && (
        <div>
          {/* Filter bar */}
          <div className="flex items-center gap-2 mb-lg">
            {(['all', 'available', 'missing'] as LibraryFilter[]).map(f => (
              <Button
                key={f}
                size="sm"
                variant={libraryFilter === f ? 'default' : 'outline'}
                onClick={() => setLibraryFilter(f)}
              >
                {f === 'all' ? 'All' : f === 'available' ? 'Available' : 'Missing'}
              </Button>
            ))}
          </div>

          {/* Library detail drill-down */}
          {renderLibraryDetail()}

          {libraryLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {Array.from({ length: 12 }).map((_, i) => <MediaCardSkeleton key={i} />)}
            </div>
          ) : filteredLibrary.length === 0 ? (
            <EmptyState
              icon={Tv}
              title={libraryFilter === 'all' ? 'No TV shows in your library yet' : `No ${libraryFilter} series found`}
              description={
                libraryFilter === 'all'
                  ? 'Switch to Browse TMDB to search and add TV shows.'
                  : 'Try changing the filter to see other series.'
              }
              action={
                libraryFilter === 'all'
                  ? { label: 'Browse TV Shows', onClick: () => setView('browse') }
                  : { label: 'Show All', onClick: () => setLibraryFilter('all') }
              }
            />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {filteredLibrary.map(s => (
                <MediaCard
                  key={s.id}
                  title={s.title}
                  year={s.year}
                  posterUrl={s.poster_url}
                  rating={s.rating}
                  status={s.status_text || undefined}
                  onClick={() => openLibDetail(s)}
                  className={cn(
                    selectedLibSeries?.id === s.id && 'ring-2 ring-accent-primary rounded-md'
                  )}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
