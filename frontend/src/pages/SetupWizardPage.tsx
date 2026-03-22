import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, ChevronRight, ChevronLeft, Loader2, Wifi, WifiOff, Film, ExternalLink, Server } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import api from '@/lib/api'

const steps = [
  { id: 'welcome', title: 'Welcome to MediaForge' },
  { id: 'jellyfin', title: 'Connect Jellyfin' },
  { id: 'services', title: 'Backend Services' },
  { id: 'tmdb', title: 'TMDB API Key' },
  { id: 'complete', title: 'All Done!' },
]

export function SetupWizardPage() {
  const [step, setStep] = useState(0)
  const navigate = useNavigate()

  // Jellyfin state
  const [jfDetecting, setJfDetecting] = useState(false)
  const [jfDetected, setJfDetected] = useState<{ url: string; server_name: string; version: string } | null>(null)
  const [jfUrl, setJfUrl] = useState('')
  const [jfUsername, setJfUsername] = useState('')
  const [jfPassword, setJfPassword] = useState('')
  const [jfConnecting, setJfConnecting] = useState(false)
  const [jfResult, setJfResult] = useState<{ success: boolean; message: string; api_key?: string } | null>(null)

  // Backend services state
  const [servicesChecking, setServicesChecking] = useState(false)
  const [servicesHealth, setServicesHealth] = useState<Record<string, boolean>>({})
  const [configuring, setConfiguring] = useState(false)
  const [configResult, setConfigResult] = useState<Record<string, boolean> | null>(null)

  // TMDB state
  const [tmdbKey, setTmdbKey] = useState('')
  const [tmdbTesting, setTmdbTesting] = useState(false)
  const [tmdbResult, setTmdbResult] = useState<{ success: boolean; message: string } | null>(null)

  // Completing
  const [completing, setCompleting] = useState(false)

  // Check if already set up
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const { data } = await api.get('/setup/status')
        if (data.is_complete) {
          navigate('/login')
        }
      } catch { /* API not ready */ }
    }
    checkStatus()
  }, [navigate])

  // Auto-detect Jellyfin when reaching step 1
  useEffect(() => {
    if (step === 1 && !jfDetected && !jfDetecting) {
      detectJellyfin()
    }
  }, [step])

  // Auto-check services when reaching step 2
  useEffect(() => {
    if (step === 2 && Object.keys(servicesHealth).length === 0) {
      checkServices()
    }
  }, [step])

  const detectJellyfin = async () => {
    setJfDetecting(true)
    try {
      const { data } = await api.post('/setup/jellyfin/detect')
      if (data.success) {
        setJfDetected({ url: data.jellyfin_url, server_name: data.server_name, version: data.version })
        setJfUrl(data.jellyfin_url)
      }
    } catch { /* Not found */ }
    finally { setJfDetecting(false) }
  }

  const connectJellyfin = async () => {
    setJfConnecting(true)
    setJfResult(null)
    try {
      const { data } = await api.post('/setup/jellyfin/connect', {
        jellyfin_url: jfUrl || 'http://192.168.2.54:8096',
        username: jfUsername,
        password: jfPassword,
      })
      setJfResult(data)
    } catch {
      setJfResult({ success: false, message: 'Connection failed. Is Jellyfin running?' })
    } finally { setJfConnecting(false) }
  }

  const checkServices = async () => {
    setServicesChecking(true)
    try {
      const { data } = await api.post('/setup/services/check')
      setServicesHealth(data.services || {})
    } catch { /* */ }
    finally { setServicesChecking(false) }
  }

  const autoConfigureServices = async () => {
    setConfiguring(true)
    try {
      const { data } = await api.post('/setup/services/configure')
      setConfigResult(data)
    } catch { /* */ }
    finally { setConfiguring(false) }
  }

  const testTmdb = async () => {
    setTmdbTesting(true)
    setTmdbResult(null)
    try {
      const { data } = await api.post('/setup/tmdb', { api_key: tmdbKey })
      setTmdbResult(data)
    } catch {
      setTmdbResult({ success: false, message: 'Failed to validate key' })
    } finally { setTmdbTesting(false) }
  }

  const finishSetup = async () => {
    setCompleting(true)
    try {
      await api.post('/setup/complete', { confirm: true })
      try {
        const { data } = await api.post('/auth/login', {
          username: jfUsername,
          password: jfPassword,
        })
        localStorage.setItem('mediaforge_token', data.token)
        localStorage.setItem('mediaforge_user', JSON.stringify(data.user))
        navigate('/')
      } catch {
        navigate('/login')
      }
    } catch {
      alert('Setup failed, please try again')
    } finally { setCompleting(false) }
  }

  const canProceed = () => {
    if (step === 1) return jfResult?.success
    if (step === 2) return true // Services step is informational
    if (step === 3) return tmdbResult?.success
    return true
  }

  const serviceNames: Record<string, string> = {
    radarr: 'Radarr (Movies)',
    sonarr: 'Sonarr (TV Shows)',
    prowlarr: 'Prowlarr (Indexers)',
    qbittorrent: 'qBittorrent (Torrents)',
    bazarr: 'Bazarr (Subtitles)',
  }

  return (
    <div className="min-h-screen bg-bg-deep flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-accent-primary rounded-lg flex items-center justify-center mx-auto mb-4">
            <Film size={32} className="text-white" />
          </div>
          <h1 className="text-page-title text-accent-primary font-bold">MediaForge</h1>
          <p className="text-body text-text-secondary mt-1">Your unified media management system</p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-1.5 mb-8">
          {steps.map((s, i) => (
            <div
              key={s.id}
              className={`h-1.5 rounded-full transition-all ${
                i < step ? 'w-8 bg-status-success' : i === step ? 'w-8 bg-accent-primary' : 'w-4 bg-bg-elevated'
              }`}
            />
          ))}
        </div>

        <Card>
          <CardContent className="p-8">
            {/* Step 0: Welcome */}
            {step === 0 && (
              <div className="text-center space-y-4">
                <h2 className="text-section-header">Let's get you set up</h2>
                <p className="text-body text-text-secondary">
                  MediaForge is a unified frontend for your entire media stack. All backend services
                  (Radarr, Sonarr, Prowlarr, qBittorrent, etc.) are installed automatically.
                </p>
                <div className="bg-bg-elevated rounded-md p-4 text-left space-y-2 text-body text-text-secondary">
                  <p>This wizard will:</p>
                  <p>1. Connect to your Jellyfin server</p>
                  <p>2. Auto-configure all backend services</p>
                  <p>3. Set up TMDB for movie/TV metadata</p>
                  <p>4. Get you ready to browse and request content</p>
                </div>
                <p className="text-caption text-text-muted">Takes about 2 minutes</p>
              </div>
            )}

            {/* Step 1: Jellyfin */}
            {step === 1 && (
              <div className="space-y-5">
                <h2 className="text-section-header">Connect to Jellyfin</h2>

                <div className="bg-bg-elevated rounded-md p-4">
                  {jfDetecting ? (
                    <div className="flex items-center gap-3 text-text-secondary">
                      <Loader2 size={18} className="animate-spin" />
                      <span>Searching for Jellyfin...</span>
                    </div>
                  ) : jfDetected ? (
                    <div className="flex items-center gap-3">
                      <Wifi size={18} className="text-status-success" />
                      <div>
                        <p className="text-body font-medium text-status-success">
                          Found: {jfDetected.server_name}
                        </p>
                        <p className="text-caption text-text-muted">{jfDetected.url} (v{jfDetected.version})</p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3 text-text-muted">
                      <WifiOff size={18} />
                      <span>Jellyfin not auto-detected. Enter URL below.</span>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-label text-text-secondary mb-1">Jellyfin URL</label>
                  <Input placeholder="http://192.168.2.54:8096" value={jfUrl} onChange={(e) => setJfUrl(e.target.value)} />
                </div>
                <div>
                  <label className="block text-label text-text-secondary mb-1">Admin Username</label>
                  <Input placeholder="Your Jellyfin admin username" value={jfUsername} onChange={(e) => setJfUsername(e.target.value)} />
                </div>
                <div>
                  <label className="block text-label text-text-secondary mb-1">Admin Password</label>
                  <Input type="password" placeholder="Password" value={jfPassword} onChange={(e) => setJfPassword(e.target.value)} />
                </div>

                <Button onClick={connectJellyfin} disabled={jfConnecting || !jfUsername || !jfPassword} className="w-full">
                  {jfConnecting ? <><Loader2 size={16} className="mr-2 animate-spin" /> Connecting...</> : 'Connect & Create API Key'}
                </Button>

                {jfResult && (
                  <div className={`rounded-md p-3 text-body ${jfResult.success ? 'bg-status-success/10 text-status-success' : 'bg-status-error/10 text-status-error'}`}>
                    {jfResult.success && <Check size={16} className="inline mr-2" />}
                    {jfResult.message}
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Backend Services */}
            {step === 2 && (
              <div className="space-y-5">
                <h2 className="text-section-header">Backend Services</h2>
                <p className="text-body text-text-secondary">
                  Checking that all backend services are running and configuring them to work together.
                </p>

                <div className="space-y-2">
                  {Object.entries(serviceNames).map(([key, label]) => (
                    <div key={key} className="flex items-center justify-between bg-bg-elevated rounded-md p-3">
                      <div className="flex items-center gap-2">
                        <Server size={16} className="text-text-muted" />
                        <span className="text-body">{label}</span>
                      </div>
                      {servicesChecking ? (
                        <Loader2 size={14} className="animate-spin text-text-muted" />
                      ) : servicesHealth[key] !== undefined ? (
                        <Badge variant={servicesHealth[key] ? 'healthy' : 'warning'}>
                          {servicesHealth[key] ? 'Ready' : 'Starting...'}
                        </Badge>
                      ) : (
                        <Badge variant="default">Checking</Badge>
                      )}
                    </div>
                  ))}
                </div>

                <div className="flex gap-2">
                  <Button onClick={checkServices} disabled={servicesChecking} variant="secondary">
                    {servicesChecking ? <><Loader2 size={14} className="mr-1 animate-spin" /> Checking...</> : 'Refresh Status'}
                  </Button>
                  <Button onClick={autoConfigureServices} disabled={configuring}>
                    {configuring ? <><Loader2 size={14} className="mr-1 animate-spin" /> Configuring...</> : 'Auto-Configure'}
                  </Button>
                </div>

                {configResult && (
                  <div className="bg-status-success/10 rounded-md p-3 text-body text-status-success">
                    <Check size={16} className="inline mr-2" />
                    Services configured! Prowlarr syncs indexers to Radarr/Sonarr, download clients are connected.
                  </div>
                )}
              </div>
            )}

            {/* Step 3: TMDB */}
            {step === 3 && (
              <div className="space-y-5">
                <h2 className="text-section-header">TMDB API Key</h2>
                <p className="text-body text-text-secondary">
                  TMDB provides movie/TV metadata, posters, and the Discover page content. You need a free API key.
                </p>
                <div className="bg-bg-elevated rounded-md p-4 space-y-2">
                  <p className="text-body font-medium">How to get one (free, 30 seconds):</p>
                  <ol className="text-body text-text-secondary space-y-1 list-decimal ml-4">
                    <li>Create an account at themoviedb.org</li>
                    <li>Go to Settings then API</li>
                    <li>Request an API key (choose Developer)</li>
                    <li>Copy the API Key (v3 auth) value</li>
                  </ol>
                  <a href="https://www.themoviedb.org/settings/api" target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-accent-primary hover:text-accent-hover text-body mt-2">
                    Open TMDB Settings <ExternalLink size={14} />
                  </a>
                </div>
                <div>
                  <label className="block text-label text-text-secondary mb-1">TMDB API Key (v3)</label>
                  <Input placeholder="Paste your key here" value={tmdbKey} onChange={(e) => setTmdbKey(e.target.value)} />
                </div>
                <Button onClick={testTmdb} disabled={tmdbTesting || !tmdbKey} className="w-full">
                  {tmdbTesting ? <><Loader2 size={16} className="mr-2 animate-spin" /> Validating...</> : 'Validate Key'}
                </Button>
                {tmdbResult && (
                  <div className={`rounded-md p-3 text-body ${tmdbResult.success ? 'bg-status-success/10 text-status-success' : 'bg-status-error/10 text-status-error'}`}>
                    {tmdbResult.success && <Check size={16} className="inline mr-2" />}
                    {tmdbResult.message}
                  </div>
                )}
              </div>
            )}

            {/* Step 4: Complete */}
            {step === 4 && (
              <div className="text-center space-y-5">
                <div className="w-16 h-16 bg-status-success/10 rounded-full flex items-center justify-center mx-auto">
                  <Check size={32} className="text-status-success" />
                </div>
                <h2 className="text-section-header">You're all set!</h2>
                <p className="text-body text-text-secondary">
                  MediaForge is configured. All backend services are wired together automatically.
                </p>
                <div className="bg-bg-elevated rounded-md p-4 text-left space-y-2 text-body text-text-secondary">
                  <p className="font-medium text-text-primary">Next steps:</p>
                  <p>- Add indexers from the Indexers page (synced via Prowlarr)</p>
                  <p>- Browse and request movies/TV from the Discover page</p>
                  <p>- Configure VPN for download protection</p>
                  <p>- Set up IPTV for live TV (optional)</p>
                </div>
                <Button onClick={finishSetup} disabled={completing} className="w-full" size="lg">
                  {completing ? <><Loader2 size={16} className="mr-2 animate-spin" /> Finishing...</> : 'Launch MediaForge'}
                </Button>
              </div>
            )}

            {/* Navigation */}
            {step < 4 && (
              <div className="flex justify-between mt-8 pt-4 border-t border-bg-elevated">
                <Button variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
                  <ChevronLeft size={16} className="mr-1" /> Back
                </Button>
                <Button onClick={() => setStep((s) => s + 1)} disabled={!canProceed()}>
                  {step === 0 ? "Let's Go" : 'Next'} <ChevronRight size={16} className="ml-1" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
