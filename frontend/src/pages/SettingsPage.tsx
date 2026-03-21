import { useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import api from '@/lib/api'

type Tab = 'general' | 'quality' | 'notifications' | 'users'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('general')
  const [jellyfinUrl, setJellyfinUrl] = useState('')
  const [jellyfinKey, setJellyfinKey] = useState('')
  const [tmdbKey, setTmdbKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState('')

  const tabs: { id: Tab; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'quality', label: 'Quality Profiles' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'users', label: 'Users' },
  ]

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
      setTestResult(jf?.status === 'healthy' ? 'Jellyfin connection OK!' : `Jellyfin: ${jf?.message || 'Unknown'}`)
    } catch {
      setTestResult('Connection test failed')
    }
  }

  return (
    <div>
      <PageHeader title="Settings" />

      {/* Tab navigation */}
      <div className="flex gap-1 mb-6 border-b border-bg-elevated">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-body transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'text-accent-primary border-accent-primary'
                : 'text-text-secondary border-transparent hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* General Settings */}
      {activeTab === 'general' && (
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
                <Button variant="secondary" onClick={testJellyfin}>Test Connection</Button>
                {testResult && <span className="text-body text-text-secondary self-center">{testResult}</span>}
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
      )}

      {activeTab === 'quality' && (
        <Card>
          <CardContent className="py-12 text-center text-text-muted">
            Quality profile editor coming soon. TRaSH Guide presets will be available here.
          </CardContent>
        </Card>
      )}

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
