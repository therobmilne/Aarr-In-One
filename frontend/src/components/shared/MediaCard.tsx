import { Star } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface MediaCardProps {
  title: string
  year?: number | null
  posterUrl?: string | null
  rating?: number | null
  status?: string
  quality?: string | null
  mediaType?: string
  onClick?: () => void
  className?: string
}

export function MediaCard({
  title,
  year,
  posterUrl,
  rating,
  status,
  quality,
  mediaType,
  onClick,
  className,
}: MediaCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'group cursor-pointer transition-all duration-150',
        'hover:-translate-y-1 hover:shadow-lg',
        className
      )}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] rounded-md overflow-hidden bg-bg-elevated mb-2">
        {posterUrl ? (
          <img
            src={posterUrl}
            alt={title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-text-muted">
            No Poster
          </div>
        )}

        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-150" />

        {/* Quality badge */}
        {quality && (
          <div className="absolute top-2 right-2">
            <Badge
              variant={
                quality.includes('4K') || quality.includes('2160')
                  ? 'warning'
                  : 'default'
              }
            >
              {quality}
            </Badge>
          </div>
        )}

        {/* Status badge */}
        {status && (
          <div className="absolute bottom-2 left-2">
            <Badge variant={status === 'available' ? 'available' : status === 'downloading' ? 'downloading' : 'pending'}>
              {status}
            </Badge>
          </div>
        )}

        {/* Media type indicator */}
        {mediaType && (
          <div className="absolute top-2 left-2">
            <Badge>{mediaType === 'tv' ? 'TV' : 'Movie'}</Badge>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="px-1">
        <h3 className="text-body font-medium text-text-primary truncate">{title}</h3>
        <div className="flex items-center gap-2 mt-0.5">
          {year && <span className="text-caption text-text-muted">{year}</span>}
          {rating != null && rating > 0 && (
            <span className="flex items-center gap-0.5 text-caption text-text-muted">
              <Star size={10} className="fill-status-warning text-status-warning" />
              {rating.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
