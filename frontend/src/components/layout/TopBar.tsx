import { useState } from 'react'
import { Search, Bell, LogOut, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export function TopBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/discover?q=${encodeURIComponent(searchQuery)}`)
      setSearchQuery('')
      setSearchOpen(false)
    }
  }

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-14 px-6 bg-bg-deep/80 backdrop-blur-sm border-b border-bg-elevated">
      {/* Search */}
      <div className="flex items-center gap-4 flex-1">
        <form onSubmit={handleSearch} className="relative max-w-md flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <Input
            placeholder="Search movies, shows, channels... (Cmd+K)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-bg-surface"
          />
        </form>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon">
          <Bell size={18} />
        </Button>

        <div className="flex items-center gap-2 ml-2">
          <div className="w-8 h-8 rounded-full bg-accent-primary/20 flex items-center justify-center">
            <User size={16} className="text-accent-primary" />
          </div>
          {user && (
            <span className="text-label text-text-secondary hidden md:inline">
              {user.display_name || user.username}
            </span>
          )}
          <Button variant="ghost" size="icon" onClick={logout} title="Logout">
            <LogOut size={16} />
          </Button>
        </div>
      </div>
    </header>
  )
}
