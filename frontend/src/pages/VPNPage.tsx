import { useEffect, useState } from 'react'
import { Shield, Power, RefreshCw, Save, Upload } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDuration } from '@/lib/utils'
import api from '@/lib/api'

interface VPNStatus {
  connected: boolean
  provider: string
  vpn_type: string
  public_ip: string | null
  forwarded_port: number | null
  kill_switch_active: boolean
  uptime_seconds: number | null
  interface: string
}

const PROVIDERS = [
  'ProtonVPN', 'Mullvad', 'AirVPN', 'PIA', 'NordVPN', 'Surfshark',
  'Custom (WireGuard)', 'Custom (OpenVPN)',
]

export function VPNPage() {
  const [status, setStatus] = useState<VPNStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')

  // Config form
  const [provider, setProvider] = useState('')
  const [connType, setConnType] = useState<'wireguard' | 'openvpn'>('wireguard')
  const [wgConfig, setWgConfig] = useState('')
  const [ovpnUser, setOvpnUser] = useState('')
  const [ovpnPass, setOvpnPass] = useState('')
  const [ovpnConfig, setOvpnConfig] = useState('')
  const [ovpnServer, setOvpnServer] = useState('')
  const [ovpnPort, setOvpnPort] = useState(1194)
  const [ovpnProtocol, setOvpnProtocol] = useState('udp')
  const [killSwitch, setKillSwitch] = useState(true)
  const [portFwd, setPortFwd] = useState(true)

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
      if (data.kill_switch !== undefined) setKillSwitch(data.kill_switch)
      if (data.port_forwarding !== undefined) setPortFwd(data.port_forwarding)
      if (data.openvpn_server) setOvpnServer(data.openvpn_server)
      if (data.openvpn_port) setOvpnPort(data.openvpn_port)
      if (data.openvpn_protocol) setOvpnProtocol(data.openvpn_protocol)
    } catch { /* not saved yet */ }
  }

  useEffect(() => {
    fetchStatus()
    fetchConfig()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleConnect = async () => {
    setLoading(true)
    try {
      await api.post('/vpn/connect')
      await fetchStatus()
    } catch { alert('Connection failed') }
    finally { setLoading(false) }
  }

  const handleDisconnect = async () => {
    setLoading(true)
    try {
      await api.post('/vpn/disconnect')
      await fetchStatus()
    } catch { alert('Disconnect failed') }
    finally { setLoading(false) }
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveMsg('')
    try {
      await api.put('/vpn/config', {
        provider,
        connection_type: connType,
        wireguard_config: connType === 'wireguard' ? wgConfig : null,
        openvpn_username: connType === 'openvpn' ? ovpnUser : null,
        openvpn_password: connType === 'openvpn' ? ovpnPass : null,
        openvpn_config: connType === 'openvpn' ? ovpnConfig : null,
        openvpn_server: connType === 'openvpn' ? ovpnServer : null,
        openvpn_port: connType === 'openvpn' ? ovpnPort : null,
        openvpn_protocol: connType === 'openvpn' ? ovpnProtocol : null,
        kill_switch: killSwitch,
        port_forwarding: portFwd,
      })
      setSaveMsg('Saved!')
      setTimeout(() => setSaveMsg(''), 3000)
    } catch { setSaveMsg('Failed to save') }
    finally { setSaving(false) }
  }

  const handleRefreshPort = async () => {
    try {
      const { data } = await api.post('/vpn/port/refresh')
      await fetchStatus()
      alert(data.port ? `Port: ${data.port}` : 'No port available')
    } catch { alert('Failed to refresh port') }
  }

  const handleFileUpload = (setter: (v: string) => void) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        const text = await file.text()
        setter(text)
      }
    }
    input.click()
  }

  return (
    <div>
      <PageHeader title="VPN" subtitle="Connection and configuration">
        {status?.connected ? (
          <Button variant="destructive" onClick={handleDisconnect} disabled={loading}>
            <Power size={16} className="mr-1" /> Disconnect
          </Button>
        ) : (
          <Button onClick={handleConnect} disabled={loading}>
            <Power size={16} className="mr-1" /> Connect
          </Button>
        )}
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
              <span className="text-label text-text-secondary">Provider</span>
              <span className="text-body">{status?.provider || provider || 'Not configured'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Type</span>
              <span className="text-body uppercase">{status?.vpn_type || connType}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Public IP</span>
              <span className="text-body font-mono">{status?.public_ip || '--'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Kill Switch</span>
              <Badge variant={status?.kill_switch_active ? 'healthy' : 'warning'}>
                {status?.kill_switch_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Port Forwarding</span>
              <div className="flex items-center gap-2">
                <span className="text-body font-mono">{status?.forwarded_port || 'None'}</span>
                <Button variant="ghost" size="sm" onClick={handleRefreshPort}><RefreshCw size={12} /></Button>
              </div>
            </div>
            {status?.uptime_seconds != null && status.uptime_seconds > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-label text-text-secondary">Uptime</span>
                <span className="text-body">{formatDuration(status.uptime_seconds)}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-label text-text-secondary mb-1">VPN Provider</label>
              <select
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value)
                  if (e.target.value.includes('WireGuard')) setConnType('wireguard')
                  if (e.target.value.includes('OpenVPN')) setConnType('openvpn')
                }}
                className="w-full h-10 rounded-sm border border-bg-elevated bg-bg-surface px-3 text-body text-text-primary"
              >
                <option value="">Select provider...</option>
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
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-label text-text-secondary">WireGuard Config (wg0.conf)</label>
                  <Button variant="ghost" size="sm" onClick={() => handleFileUpload(setWgConfig)}>
                    <Upload size={12} className="mr-1" /> Upload
                  </Button>
                </div>
                <textarea
                  value={wgConfig}
                  onChange={(e) => setWgConfig(e.target.value)}
                  placeholder="Paste wg0.conf contents or upload file..."
                  rows={6}
                  className="w-full rounded-sm border border-bg-elevated bg-bg-surface px-3 py-2 text-body text-text-primary font-mono text-[12px] placeholder:text-text-muted"
                />
              </div>
            )}

            {connType === 'openvpn' && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-label text-text-secondary mb-1">Username</label>
                    <Input value={ovpnUser} onChange={(e) => setOvpnUser(e.target.value)} placeholder="VPN username" />
                  </div>
                  <div>
                    <label className="block text-label text-text-secondary mb-1">Password</label>
                    <Input type="password" value={ovpnPass} onChange={(e) => setOvpnPass(e.target.value)} placeholder="VPN password" />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-label text-text-secondary mb-1">Server</label>
                    <Input value={ovpnServer} onChange={(e) => setOvpnServer(e.target.value)} placeholder="vpn.example.com" />
                  </div>
                  <div>
                    <label className="block text-label text-text-secondary mb-1">Port</label>
                    <Input type="number" value={ovpnPort} onChange={(e) => setOvpnPort(Number(e.target.value))} />
                  </div>
                  <div>
                    <label className="block text-label text-text-secondary mb-1">Protocol</label>
                    <select
                      value={ovpnProtocol}
                      onChange={(e) => setOvpnProtocol(e.target.value)}
                      className="w-full h-10 rounded-sm border border-bg-elevated bg-bg-surface px-3 text-body text-text-primary"
                    >
                      <option value="udp">UDP</option>
                      <option value="tcp">TCP</option>
                    </select>
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-label text-text-secondary">OpenVPN Config (.ovpn)</label>
                    <Button variant="ghost" size="sm" onClick={() => handleFileUpload(setOvpnConfig)}>
                      <Upload size={12} className="mr-1" /> Upload
                    </Button>
                  </div>
                  <textarea
                    value={ovpnConfig}
                    onChange={(e) => setOvpnConfig(e.target.value)}
                    placeholder="Paste .ovpn contents or upload file (optional if server/port set above)..."
                    rows={4}
                    className="w-full rounded-sm border border-bg-elevated bg-bg-surface px-3 py-2 text-body text-text-primary font-mono text-[12px] placeholder:text-text-muted"
                  />
                </div>
              </>
            )}

            <div className="flex items-center gap-6">
              <label className="flex items-center gap-2 text-body cursor-pointer">
                <input type="checkbox" checked={killSwitch} onChange={(e) => setKillSwitch(e.target.checked)}
                  className="w-4 h-4 rounded accent-accent-primary" />
                Kill Switch
              </label>
              <label className="flex items-center gap-2 text-body cursor-pointer">
                <input type="checkbox" checked={portFwd} onChange={(e) => setPortFwd(e.target.checked)}
                  className="w-4 h-4 rounded accent-accent-primary" />
                Port Forwarding
              </label>
            </div>

            <div className="flex items-center gap-3">
              <Button onClick={handleSave} disabled={saving}>
                <Save size={14} className="mr-1" /> {saving ? 'Saving...' : 'Save Config'}
              </Button>
              {saveMsg && <span className="text-body text-status-success">{saveMsg}</span>}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
