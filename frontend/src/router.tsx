import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { DashboardSkeleton } from '@/components/shared/LoadingSkeleton'

// Lazy-loaded pages
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const LoginPage = lazy(() => import('@/pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const DiscoverPage = lazy(() => import('@/pages/DiscoverPage').then((m) => ({ default: m.DiscoverPage })))
const MoviesPage = lazy(() => import('@/pages/MoviesPage').then((m) => ({ default: m.MoviesPage })))
const SeriesPage = lazy(() => import('@/pages/SeriesPage').then((m) => ({ default: m.SeriesPage })))
const LiveTVPage = lazy(() => import('@/pages/LiveTVPage').then((m) => ({ default: m.LiveTVPage })))
const DownloadsPage = lazy(() => import('@/pages/DownloadsPage').then((m) => ({ default: m.DownloadsPage })))
const IndexersPage = lazy(() => import('@/pages/IndexersPage').then((m) => ({ default: m.IndexersPage })))
const SubtitlesPage = lazy(() => import('@/pages/SubtitlesPage').then((m) => ({ default: m.SubtitlesPage })))
const VPNPage = lazy(() => import('@/pages/VPNPage').then((m) => ({ default: m.VPNPage })))
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))
const SetupWizardPage = lazy(() => import('@/pages/SetupWizardPage').then((m) => ({ default: m.SetupWizardPage })))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })))

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<DashboardSkeleton />}>{children}</Suspense>
}

const routes: RouteObject[] = [
  {
    path: '/login',
    element: <SuspenseWrapper><LoginPage /></SuspenseWrapper>,
  },
  {
    path: '/setup',
    element: <SuspenseWrapper><SetupWizardPage /></SuspenseWrapper>,
  },
  {
    element: <AppShell />,
    children: [
      { index: true, element: <SuspenseWrapper><DashboardPage /></SuspenseWrapper> },
      { path: 'discover', element: <SuspenseWrapper><DiscoverPage /></SuspenseWrapper> },
      { path: 'movies', element: <SuspenseWrapper><MoviesPage /></SuspenseWrapper> },
      { path: 'series', element: <SuspenseWrapper><SeriesPage /></SuspenseWrapper> },
      { path: 'livetv', element: <SuspenseWrapper><LiveTVPage /></SuspenseWrapper> },
      { path: 'downloads', element: <SuspenseWrapper><DownloadsPage /></SuspenseWrapper> },
      { path: 'indexers', element: <SuspenseWrapper><IndexersPage /></SuspenseWrapper> },
      { path: 'subtitles', element: <SuspenseWrapper><SubtitlesPage /></SuspenseWrapper> },
      { path: 'vpn', element: <SuspenseWrapper><VPNPage /></SuspenseWrapper> },
      { path: 'settings', element: <SuspenseWrapper><SettingsPage /></SuspenseWrapper> },
      { path: '*', element: <SuspenseWrapper><NotFoundPage /></SuspenseWrapper> },
    ],
  },
]

export const router = createBrowserRouter(routes)
