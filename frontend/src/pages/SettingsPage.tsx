import { useState, useEffect, useRef, useCallback } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import api from '@/lib/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Tab = 'general' | 'iptv' | 'downloads' | 'usenet' | 'notifications' | 'users'

interface UsenetServer {
  id: string
  hostname: string
  port: number
  ssl: boolean
  username: string
  password: string
  connections: number
  priority: 'primary' | 'backup'
  testResult?: string
}

interface ScanStatus {
  running: boolean
  phase: string
  movies_found: number
  series_found: number
  live_channels_found: number
  skipped: number
  progress: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId() {
  return Math.random().toString(36).substring(2, 10)
}

function formatNumber(n: number) {
  return n.toLocaleString()
}

// ---------------------------------------------------------------------------
// Tab: General
// ---------------------------------------------------------------------------

function GeneralTab() {
  const [jellyfinUrl, setJellyfinUrl] = useState('')
  const [jellyfinKey, setJellyfinKey] = useState('')
  const [tmdbKey, setTmdbKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState('')

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.put('/system/settings', {
        jellyfin_url: jellyfinUrl,
        jellyfin_api_key: jellyfinKey,
        tmdb_api_key: tmdbKey,
      })
      setTestResult('Settings saved!')
    } catch {
      setTestResult('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const testJellyfin = async () => {
    try {
      const { data } = await api.get('/system/health')
      const jf = data.subsystems?.find((s: { name: string }) => s.name === 'jellyfin')
      setTestResult(
        jf?.status === 'healthy'
          ? 'Jellyfin connection OK!'
          : `Jellyfin: ${jf?.message || 'Unknown'}`
      )
    } catch {
      setTestResult('Connection test failed')
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Jellyfin Connection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-label text-text-secondary mb-1">Jellyfin URL</label>
            <Input
              placeholder="http://192.168.2.50:8096"
              value={jellyfinUrl}
              onChange={(e) => setJellyfinUrl(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-label text-text-secondary mb-1">API Key</label>
            <Input
              type="password"
              placeholder="Jellyfin API key"
              value={jellyfinKey}
              onChange={(e) => setJellyfinKey(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={testJellyfin}>
              Test Connection
            </Button>
            {testResult && (
              <span className="text-body text-text-secondary self-center">{testResult}</span>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>TMDB</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-label text-text-secondary mb-1">TMDB API Key</label>
            <Input
              type="password"
              placeholder="TMDB API v3 key"
              value={tmdbKey}
              onChange={(e) => setTmdbKey(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving}>
        {saving ? 'Saving...' : 'Save Settings'}
      </Button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: IPTV
// ---------------------------------------------------------------------------

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard may not be available
    }
  }

  return (
    <Button variant="secondary" size="sm" onClick={handleCopy}>
      {copied ? 'Copied!' : 'Copy'}
    </Button>
  )
}

function IptvTab() {
  const [serverUrl, setServerUrl] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [testResult, setTestResult] = useState<string | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null)
  const [scanComplete, setScanComplete] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  const handleTestConnection = async () => {
    setTestLoading(true)
    setTestResult(null)
    try {
      const { data } = await api.post('/iptv/test', {
        server_url: serverUrl,
        username,
        password,
      })
      setTestResult(
        `Connection successful! Found ${formatNumber(data.movies ?? 0)} movies, ${formatNumber(data.series ?? 0)} series, ${formatNumber(data.live_channels ?? 0)} live channels.`
      )
    } catch {
      setTestResult('Connection failed. Check your credentials and server URL.')
    } finally {
      setTestLoading(false)
    }
  }

  const handleScanLibrary = async () => {
    setScanning(true)
    setScanComplete(false)
    setScanStatus(null)
    try {
      await api.post('/iptv/scan')
      // start polling
      pollRef.current = setInterval(async () => {
        try {
          const { data } = await api.get('/iptv/scan/status')
          setScanStatus(data)
          if (!data.running) {
            stopPolling()
            setScanning(false)
            setScanComplete(true)
          }
        } catch {
          stopPolling()
          setScanning(false)
        }
      }, 2000)
    } catch {
      setScanning(false)
    }
  }

  const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8686'

  return (
    <div className="max-w-2xl space-y-6">
      {/* IPTV Server Config */}
      <Card>
        <CardHeader>
          <CardTitle>IPTV Server</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-label text-text-secondary mb-1">Server URL</label>
            <Input
              placeholder="http://provider.example.com:8080"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-label text-text-secondary mb-1">Username</label>
            <Input
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-label text-text-secondary mb-1">Password</label>
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="secondary" onClick={handleTestConnection} disabled={testLoading}>
              {testLoading ? 'Testing...' : 'Test Connection'}
            </Button>
            <Button onClick={handleScanLibrary} disabled={scanning}>
              {scanning ? 'Scanning...' : 'Scan Library'}
            </Button>
          </div>
          {testResult && (
            <p className="text-body text-text-secondary">{testResult}</p>
          )}
        </CardContent>
      </Card>

      {/* Scan Progress */}
      {(scanning || scanStatus) && (
        <Card>
          <CardHeader>
            <CardTitle>Scan Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {scanStatus && (
              <>
                <div className="flex items-center gap-2">
                  <Badge variant={scanStatus.running ? 'downloading' : 'success'}>
                    {scanStatus.running ? 'Scanning' : 'Complete'}
                  </Badge>
                  <span className="text-body text-text-primary">{scanStatus.phase}</span>
                </div>
                <p className="text-body text-text-secondary">
                  Found {formatNumber(scanStatus.movies_found)} movies,{' '}
                  {formatNumber(scanStatus.series_found)} TV shows,{' '}
                  {formatNumber(scanStatus.live_channels_found)} live channels
                </p>
                <Progress value={scanStatus.progress} />
                <p className="text-caption text-text-muted">
                  {scanStatus.progress}% complete &middot; Skipped{' '}
                  {formatNumber(scanStatus.skipped)} existing items
                </p>
              </>
            )}
            {!scanStatus && scanning && (
              <p className="text-body text-text-secondary">Starting scan...</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Output URLs */}
      {scanComplete && (
        <Card>
          <CardHeader>
            <CardTitle>Output URLs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-caption text-text-muted">
              Add these URLs to Jellyfin or any IPTV player.
            </p>
            <OutputUrlRow
              label="M3U Playlist URL"
              url={`http://${host}/api/v1/livetv/output/m3u`}
            />
            <OutputUrlRow
              label="EPG URL"
              url={`http://${host}/api/v1/livetv/epg.xml`}
            />
            <OutputUrlRow
              label="HDHomeRun URL"
              url={`http://${host}/discover.json`}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function OutputUrlRow({ label, url }: { label: string; url: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <p className="text-label text-text-secondary mb-0.5">{label}</p>
        <code className="block text-caption text-text-primary bg-bg-elevated rounded-sm px-2 py-1.5 truncate">
          {url}
        </code>
      </div>
      <CopyButton text={url} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: Downloads
// ---------------------------------------------------------------------------

const QUALITY_OPTIONS = ['Any', '720p', '1080p', '2160p/4K'] as const

function DownloadsTab() {
  const [movieQuality, setMovieQuality] = useState('1080p')
  const [tvQuality, setTvQuality] = useState('1080p')
  const [minSeeders, setMinSeeders] = useState(5)
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState('')

  const handleSave = async () => {
    setSaving(true)
    setSaveResult('')
    try {
      await api.put('/system/settings', {
        default_movie_quality: movieQuality,
        default_tv_quality: tvQuality,
        minimum_seeders: minSeeders,
      })
      setSaveResult('Settings saved!')
    } catch {
      setSaveResult('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Download Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-label text-text-secondary mb-1">
              Default Movie Quality
            </label>
            <select
              className="flex h-10 w-full rounded-sm border border-bg-elevated bg-bg-surface px-3 py-2 text-body text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
              value={movieQuality}
              onChange={(e) => setMovieQuality(e.target.value)}
            >
              {QUALITY_OPTIONS.map((q) => (
                <option key={q} value={q}>
                  {q}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-label text-text-secondary mb-1">
              Default TV Quality
            </label>
            <select
              className="flex h-10 w-full rounded-sm border border-bg-elevated bg-bg-surface px-3 py-2 text-body text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
              value={tvQuality}
              onChange={(e) => setTvQuality(e.target.value)}
            >
              {QUALITY_OPTIONS.map((q) => (
                <option key={q} value={q}>
                  {q}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-label text-text-secondary mb-1">Minimum Seeders</label>
            <Input
              type="number"
              min={0}
              value={minSeeders}
              onChange={(e) => setMinSeeders(Number(e.target.value))}
              className="max-w-[200px]"
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
        {saveResult && (
          <span className="text-body text-text-secondary">{saveResult}</span>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab: Usenet
// ---------------------------------------------------------------------------

function emptyServer(): UsenetServer {
  return {
    id: generateId(),
    hostname: '',
    port: 563,
    ssl: true,
    username: '',
    password: '',
    connections: 8,
    priority: 'primary',
  }
}

function UsenetTab() {
  const [servers, setServers] = useState<UsenetServer[]>([emptyServer()])
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState('')

  const updateServer = (id: string, patch: Partial<UsenetServer>) => {
    setServers((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)))
  }

  const removeServer = (id: string) => {
    setServers((prev) => prev.filter((s) => s.id !== id))
  }

  const addServer = () => {
    setServers((prev) => [...prev, emptyServer()])
  }

  const testServer = async (server: UsenetServer) => {
    updateServer(server.id, { testResult: 'Testing...' })
    try {
      await api.post('/usenet/test', {
        hostname: server.hostname,
        port: server.port,
        ssl: server.ssl,
        username: server.username,
        password: server.password,
        connections: server.connections,
      })
      updateServer(server.id, { testResult: 'Connection OK!' })
    } catch {
      updateServer(server.id, { testResult: 'Connection failed' })
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveResult('')
    try {
      await api.put('/system/settings', {
        usenet_servers: servers.map(({ id, testResult, ...rest }) => rest),
      })
      setSaveResult('Settings saved!')
    } catch {
      setSaveResult('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      {servers.map((server, idx) => (
        <Card key={server.id}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Server {idx + 1}</CardTitle>
              {servers.length > 1 && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => removeServer(server.id)}
                >
                  Delete
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-label text-text-secondary mb-1">Hostname</label>
                <Input
                  placeholder="news.provider.com"
                  value={server.hostname}
                  onChange={(e) => updateServer(server.id, { hostname: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">Port</label>
                <Input
                  type="number"
                  value={server.port}
                  onChange={(e) => updateServer(server.id, { port: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">Username</label>
                <Input
                  placeholder="Username"
                  value={server.username}
                  onChange={(e) => updateServer(server.id, { username: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">Password</label>
                <Input
                  type="password"
                  placeholder="Password"
                  value={server.password}
                  onChange={(e) => updateServer(server.id, { password: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">Connections</label>
                <Input
                  type="number"
                  min={1}
                  max={50}
                  value={server.connections}
                  onChange={(e) => updateServer(server.id, { connections: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-label text-text-secondary mb-1">Priority</label>
                <select
                  className="flex h-10 w-full rounded-sm border border-bg-elevated bg-bg-surface px-3 py-2 text-body text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
                  value={server.priority}
                  onChange={(e) =>
                    updateServer(server.id, {
                      priority: e.target.value as 'primary' | 'backup',
                    })
                  }
                >
                  <option value="primary">Primary</option>
                  <option value="backup">Backup</option>
                </select>
              </div>
            </div>

            {/* SSL toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={server.ssl}
                onChange={(e) => updateServer(server.id, { ssl: e.target.checked })}
                className="h-4 w-4 rounded border-bg-elevated text-accent-primary focus:ring-accent-primary"
              />
              <span className="text-body text-text-primary">Use SSL/TLS</span>
            </label>

            {/* Test button */}
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => testServer(server)}
              >
                Test Connection
              </Button>
              {server.testResult && (
                <span className="text-caption text-text-secondary">{server.testResult}</span>
              )}
            </div>
          </CardContent>
        </Card>
      ))}

      <Button variant="outline" onClick={addServer}>
        + Add Server
      </Button>

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
        {saveResult && (
          <span className="text-body text-text-secondary">{saveResult}</span>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Settings Page
// ---------------------------------------------------------------------------

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('general')

  const tabs: { id: Tab; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'iptv', label: 'IPTV' },
    { id: 'downloads', label: 'Downloads' },
    { id: 'usenet', label: 'Usenet' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'users', label: 'Users' },
  ]

  return (
    <div>
      <PageHeader title="Settings" />

      {/* Tab navigation */}
      <div className="flex gap-1 mb-6 border-b border-bg-elevated overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-body transition-colors border-b-2 whitespace-nowrap ${
              activeTab === tab.id
                ? 'text-accent-primary border-accent-primary'
                : 'text-text-secondary border-transparent hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'general' && <GeneralTab />}
      {activeTab === 'iptv' && <IptvTab />}
      {activeTab === 'downloads' && <DownloadsTab />}
      {activeTab === 'usenet' && <UsenetTab />}

      {activeTab === 'notifications' && (
        <Card>
          <CardContent className="py-12 text-center text-text-muted">
            Configure Discord, email, ntfy, and other notification agents here.
          </CardContent>
        </Card>
      )}

      {activeTab === 'users' && (
        <Card>
          <CardContent className="py-12 text-center text-text-muted">
            User management synced from Jellyfin. Configure roles and auto-approve settings.
          </CardContent>
        </Card>
      )}
    </div>
  )
}
