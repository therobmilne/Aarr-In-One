import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Search,
  Film,
  Tv,
  Radio,
  Download,
  Globe,
  Subtitles,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { ROUTES } from '@/lib/constants'

const navItems = [
  { path: ROUTES.DASHBOARD, label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'power_user', 'basic_user'] },
  { path: ROUTES.DISCOVER, label: 'Discover', icon: Search, roles: ['admin', 'power_user', 'basic_user'] },
  { path: ROUTES.MOVIES, label: 'Movies', icon: Film, roles: ['admin', 'power_user'] },
  { path: ROUTES.SERIES, label: 'TV Shows', icon: Tv, roles: ['admin', 'power_user'] },
  { path: ROUTES.LIVETV, label: 'Live TV', icon: Radio, roles: ['admin', 'power_user'] },
  { path: ROUTES.DOWNLOADS, label: 'Downloads', icon: Download, roles: ['admin', 'power_user'] },
  { path: ROUTES.INDEXERS, label: 'Indexers', icon: Globe, roles: ['admin', 'power_user'] },
  { path: ROUTES.SUBTITLES, label: 'Subtitles', icon: Subtitles, roles: ['admin', 'power_user'] },
  { path: ROUTES.VPN, label: 'VPN', icon: Shield, roles: ['admin', 'power_user'] },
  { path: ROUTES.SETTINGS, label: 'Settings', icon: Settings, roles: ['admin'] },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { user } = useAuth()

  const visibleItems = navItems.filter(
    (item) => user && item.roles.includes(user.role)
  )

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-full bg-bg-surface border-r border-bg-elevated z-40',
        'flex flex-col transition-[width] duration-200',
        collapsed ? 'w-16' : 'w-56'
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-14 px-4 border-b border-bg-elevated">
        {!collapsed && (
          <span className="text-section-header text-accent-primary font-bold">
            MediaForge
          </span>
        )}
        {collapsed && (
          <span className="text-section-header text-accent-primary font-bold mx-auto">
            MF
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {visibleItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-4 py-2.5 mx-2 rounded-sm text-body transition-colors',
                isActive
                  ? 'bg-accent-primary/10 text-accent-primary'
                  : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
              )
            }
          >
            <item.icon size={20} className="shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-bg-elevated text-text-muted hover:text-text-primary transition-colors"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  )
}
