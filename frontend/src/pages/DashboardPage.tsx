import { useEffect, useState } from 'react'
import { Shield, Download, HardDrive, MessageSquare } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatusCard } from '@/components/widgets/StatusCard'
import { ActivityFeed } from '@/components/widgets/ActivityFeed'
import { DownloadQueue } from '@/components/widgets/DownloadQueue'
import { useAuth } from '@/hooks/useAuth'
import { formatBytes } from '@/lib/utils'
import api from '@/lib/api'

interface HealthData {
  status: string
  subsystems: { name: string; status: string; message: string }[]
}

export function DashboardPage() {
  const { user } = useAuth()
  const [health, setHealth] = useState<HealthData | null>(null)
  const [diskFree, setDiskFree] = useState<string>('--')

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
    fetchHealth()
    fetchInfo()
    const interval = setInterval(fetchHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const vpnStatus = health?.subsystems.find((s) => s.name === 'vpn')
  const vpnConnected = vpnStatus?.status === 'healthy'

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
          value="0 active"
          status="info"
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
          label="Requests"
          value="0 pending"
          status="info"
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
