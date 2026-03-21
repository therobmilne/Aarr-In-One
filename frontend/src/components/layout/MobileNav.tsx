import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Search, Download, Radio, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ROUTES } from '@/lib/constants'

const tabs = [
  { path: ROUTES.DASHBOARD, label: 'Home', icon: LayoutDashboard },
  { path: ROUTES.DISCOVER, label: 'Discover', icon: Search },
  { path: ROUTES.DOWNLOADS, label: 'Downloads', icon: Download },
  { path: ROUTES.LIVETV, label: 'Live TV', icon: Radio },
  { path: ROUTES.SETTINGS, label: 'Settings', icon: Settings },
]

export function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-bg-surface border-t border-bg-elevated md:hidden">
      <div className="flex items-center justify-around h-16">
        {tabs.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-1 px-3 py-2 min-w-[64px]',
                isActive ? 'text-accent-primary' : 'text-text-muted'
              )
            }
          >
            <tab.icon size={20} />
            <span className="text-[10px] font-medium">{tab.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
