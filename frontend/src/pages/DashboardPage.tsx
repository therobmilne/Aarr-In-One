import { useEffect, useState } from 'react'
import { Shield, Download, HardDrive, MessageSquare } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatusCard } from '@/components/widgets/StatusCard'
import { ActivityFeed } from '@/components/widgets/ActivityFeed'
import { DownloadQueue } from '@/components/widgets/DownloadQueue'
import { useAuth } from '@/hooks/useAuth'
import { formatBytes } from '@/lib/utils'
import api from '@/lib/api'

interface ServiceHealth {
  status: string
  code: number
}

interface HealthData {
  status: string
  services: Record<string, ServiceHealth>
}

export function DashboardPage() {
  const { user } = useAuth()
  const [health, setHealth] = useState<HealthData | null>(null)
  const [diskFree, setDiskFree] = useState<string>('--')
  const [activeDownloads, setActiveDownloads] = useState(0)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const { data } = await api.get('/system/health')
        setHealth(data)
      } catch {
        // Backend not ready
      }
    }
    const fetchInfo = async () => {
      try {
        const { data } = await api.get('/system/info')
        if (data.disk?.length > 0) {
          const mediaDisk = data.disk.find((d: { path: string }) => d.path.includes('media')) || data.disk[0]
          setDiskFree(formatBytes(mediaDisk.free_bytes))
        }
      } catch {
        // Admin only
      }
    }
    const fetchDownloads = async () => {
      try {
        const { data } = await api.get('/downloads/stats')
        setActiveDownloads(data.active || 0)
      } catch {
        // Not critical
      }
    }
    fetchHealth()
    fetchInfo()
    fetchDownloads()
    const interval = setInterval(() => { fetchHealth(); fetchDownloads() }, 30000)
    return () => clearInterval(interval)
  }, [])

  const vpnConnected = health?.services?.gluetun?.status === 'healthy'
  const servicesHealthy = health ? Object.values(health.services).filter(s => s.status === 'healthy').length : 0
  const servicesTotal = health ? Object.keys(health.services).length : 0

  return (
    <div>
      <PageHeader
        title={`Welcome back${user?.display_name ? `, ${user.display_name}` : ''}`}
      />

      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatusCard
          icon={Shield}
          label="VPN"
          value={vpnConnected ? 'Connected' : 'Disconnected'}
          status={vpnConnected ? 'success' : 'error'}
        />
        <StatusCard
          icon={Download}
          label="Downloads"
          value={`${activeDownloads} active`}
          status={activeDownloads > 0 ? 'warning' : 'info'}
        />
        <StatusCard
          icon={HardDrive}
          label="Disk Space"
          value={diskFree}
          status="info"
          subtitle="free"
        />
        <StatusCard
          icon={MessageSquare}
          label="Services"
          value={`${servicesHealthy}/${servicesTotal}`}
          status={servicesHealthy === servicesTotal ? 'success' : 'warning'}
          subtitle="healthy"
        />
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivityFeed />
        <DownloadQueue />
      </div>
    </div>
  )
}
