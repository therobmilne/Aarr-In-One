export const ROUTES = {
  DASHBOARD: '/',
  LOGIN: '/login',
  DISCOVER: '/discover',
  MOVIES: '/movies',
  SERIES: '/series',
  LIVETV: '/livetv',
  DOWNLOADS: '/downloads',
  INDEXERS: '/indexers',
  SUBTITLES: '/subtitles',
  VPN: '/vpn',
  SETTINGS: '/settings',
  SETUP: '/setup',
} as const

export const STATUS_COLORS = {
  healthy: 'text-status-success',
  success: 'text-status-success',
  available: 'text-status-success',
  completed: 'text-status-success',
  warning: 'text-status-warning',
  pending: 'text-status-warning',
  downloading: 'text-status-warning',
  error: 'text-status-error',
  failed: 'text-status-error',
  info: 'text-status-info',
  searching: 'text-status-info',
} as const

export const STATUS_BG_COLORS = {
  healthy: 'bg-status-success/10 text-status-success',
  success: 'bg-status-success/10 text-status-success',
  available: 'bg-status-success/10 text-status-success',
  warning: 'bg-status-warning/10 text-status-warning',
  pending: 'bg-status-warning/10 text-status-warning',
  downloading: 'bg-status-info/10 text-status-info',
  error: 'bg-status-error/10 text-status-error',
  failed: 'bg-status-error/10 text-status-error',
} as const
