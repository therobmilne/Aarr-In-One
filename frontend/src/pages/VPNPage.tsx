import { useEffect, useState } from 'react'
import { Shield, RefreshCw, Save, Globe, Server } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import api from '@/lib/api'

interface VPNStatus {
  connected: boolean
  public_ip: string | null
  region: string | null
  country: string | null
  status?: string
}

const PROVIDERS = [
  'protonvpn', 'mullvad', 'airvpn', 'private internet access',
  'nordvpn', 'surfshark', 'windscribe', 'custom',
]

export function VPNPage() {
  const [status, setStatus] = useState<VPNStatus | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [restarting, setRestarting] = useState(false)
  const [forwardedPort, setForwardedPort] = useState<number | null>(null)

  // Config form
  const [provider, setProvider] = useState('protonvpn')
  const [connType, setConnType] = useState<'wireguard' | 'openvpn'>('wireguard')
  const [privateKey, setPrivateKey] = useState('')
  const [addresses, setAddresses] = useState('')
  const [country, setCountry] = useState('Canada')

  const fetchStatus = async () => {
    try {
      const { data } = await api.get('/vpn/status')
      setStatus(data)
    } catch { /* not ready */ }
  }

  const fetchConfig = async () => {
    try {
      const { data } = await api.get('/vpn/config')
      if (data.provider) setProvider(data.provider)
      if (data.connection_type) setConnType(data.connection_type)
      if (data.country) setCountry(data.country)
    } catch { /* not saved yet */ }
  }

  const fetchPort = async () => {
    try {
      const { data } = await api.get('/vpn/port')
      setForwardedPort(data.port)
    } catch { /* no port */ }
  }

  useEffect(() => {
    fetchStatus()
    fetchConfig()
    fetchPort()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSaveMsg('')
    try {
      await api.put('/vpn/config', {
        provider,
        connection_type: connType,
        private_key: privateKey || undefined,
        addresses: addresses || undefined,
        country,
      })
      setSaveMsg('Saved! Restart Gluetun to apply.')
      setTimeout(() => setSaveMsg(''), 5000)
    } catch { setSaveMsg('Failed to save') }
    finally { setSaving(false) }
  }

  const handleRestart = async () => {
    setRestarting(true)
    try {
      await api.post('/vpn/restart')
      setSaveMsg('Gluetun restarting...')
      // Wait for it to come back
      setTimeout(() => { fetchStatus(); setRestarting(false) }, 10000)
    } catch {
      setSaveMsg('Restart failed')
      setRestarting(false)
    }
  }

  return (
    <div>
      <PageHeader title="VPN" subtitle="Gluetun VPN tunnel configuration">
        <Button onClick={handleRestart} disabled={restarting} variant="secondary">
          <RefreshCw size={16} className={`mr-1 ${restarting ? 'animate-spin' : ''}`} />
          {restarting ? 'Restarting...' : 'Restart VPN'}
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield size={18} /> Connection Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Status</span>
              <Badge variant={status?.connected ? 'healthy' : 'error'}>
                {status?.connected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Public IP</span>
              <span className="text-body font-mono">{status?.public_ip || '--'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Country</span>
              <span className="text-body">{status?.country || '--'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Region</span>
              <span className="text-body">{status?.region || '--'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Port Forwarding</span>
              <span className="text-body font-mono">{forwardedPort || 'None'}</span>
            </div>
            <p className="text-caption text-text-muted mt-2">
              VPN is managed by Gluetun. qBittorrent and SABnzbd route all traffic through this tunnel.
            </p>
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server size={18} /> Gluetun Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-label text-text-secondary mb-1">VPN Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full h-10 rounded-sm border border-bg-elevated bg-bg-surface px-3 text-body text-text-primary"
              >
                {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>

            <div>
              <label className="block text-label text-text-secondary mb-1">Connection Type</label>
              <div className="flex gap-2">
                <Button
                  variant={connType === 'wireguard' ? 'default' : 'secondary'}
                  size="sm"
                  onClick={() => setConnType('wireguard')}
                >WireGuard</Button>
                <Button
                  variant={connType === 'openvpn' ? 'default' : 'secondary'}
                  size="sm"
                  onClick={() => setConnType('openvpn')}
                >OpenVPN</Button>
              </div>
            </div>

            {connType === 'wireguard' && (
              <>
                <div>
                  <label className="block text-label text-text-secondary mb-1">WireGuard Private Key</label>
                  <Input
                    type="password"
                    value={privateKey}
                    onChange={(e) => setPrivateKey(e.target.value)}
                    placeholder="WireGuard private key from your VPN provider"
                  />
                </div>
                <div>
                  <label className="block text-label text-text-secondary mb-1">WireGuard Addresses</label>
                  <Input
                    value={addresses}
                    onChange={(e) => setAddresses(e.target.value)}
                    placeholder="e.g. 10.2.0.2/32"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-label text-text-secondary mb-1">Server Country</label>
              <Input
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="e.g. Canada, Netherlands"
              />
            </div>

            <div className="flex items-center gap-3">
              <Button onClick={handleSave} disabled={saving}>
                <Save size={14} className="mr-1" /> {saving ? 'Saving...' : 'Save Config'}
              </Button>
              <Button variant="secondary" onClick={handleRestart} disabled={restarting}>
                <RefreshCw size={14} className="mr-1" /> Apply & Restart
              </Button>
              {saveMsg && <span className="text-body text-status-success">{saveMsg}</span>}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
