import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { MobileNav } from './MobileNav'
import { useIsDesktop } from '@/hooks/useMediaQuery'

export function AppShell() {
  const isDesktop = useIsDesktop()

  return (
    <div className="min-h-screen bg-bg-deep">
      {isDesktop && <Sidebar />}
      <div className={isDesktop ? 'ml-56' : ''}>
        <TopBar />
        <main className="p-4 md:p-6 pb-20 md:pb-6">
          <Outlet />
        </main>
      </div>
      {!isDesktop && <MobileNav />}
    </div>
  )
}
