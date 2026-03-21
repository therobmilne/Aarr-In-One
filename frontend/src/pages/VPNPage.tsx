import { useEffect, useState } from 'react'
import { Shield, Power, RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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

export function VPNPage() {
  const [status, setStatus] = useState<VPNStatus | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchStatus = async () => {
    try {
      const { data } = await api.get('/vpn/status')
      setStatus(data)
    } catch {
      // Not ready
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleConnect = async () => {
    setLoading(true)
    try {
      await api.post('/vpn/connect')
      await fetchStatus()
    } catch {
      alert('Connection failed')
    } finally {
      setLoading(false)
    }
  }

  const handleDisconnect = async () => {
    setLoading(true)
    try {
      await api.post('/vpn/disconnect')
      await fetchStatus()
    } catch {
      alert('Disconnect failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader title="VPN" subtitle="Connection status and configuration">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield size={18} />
              Connection Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Status</span>
              <Badge variant={status?.connected ? 'healthy' : 'error'}>
                {status?.connected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Provider</span>
              <span className="text-body">{status?.provider || 'Not configured'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Type</span>
              <span className="text-body uppercase">{status?.vpn_type || '--'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Public IP</span>
              <span className="text-body font-mono">{status?.public_ip || '--'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Interface</span>
              <span className="text-body font-mono">{status?.interface || 'tun0'}</span>
            </div>
            {status?.uptime_seconds != null && (
              <div className="flex items-center justify-between">
                <span className="text-label text-text-secondary">Uptime</span>
                <span className="text-body">{formatDuration(status.uptime_seconds)}</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Security</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Kill Switch</span>
              <Badge variant={status?.kill_switch_active ? 'healthy' : 'warning'}>
                {status?.kill_switch_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-label text-text-secondary">Port Forwarding</span>
              <span className="text-body font-mono">
                {status?.forwarded_port || 'None'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
