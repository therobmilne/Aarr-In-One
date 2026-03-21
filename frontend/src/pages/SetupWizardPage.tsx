import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import api from '@/lib/api'

const steps = [
  { id: 'jellyfin', title: 'Jellyfin Connection' },
  { id: 'paths', title: 'Media Paths' },
  { id: 'vpn', title: 'VPN Setup' },
  { id: 'indexers', title: 'Indexers' },
  { id: 'quality', title: 'Quality Profiles' },
  { id: 'complete', title: 'Review & Launch' },
]

export function SetupWizardPage() {
  const [step, setStep] = useState(0)
  const [config, setConfig] = useState({
    jellyfin_url: '',
    jellyfin_api_key: '',
    media_dir: '/media',
    download_dir: '/downloads',
    vpn_provider: '',
    vpn_type: 'wireguard',
  })
  const navigate = useNavigate()

  const updateConfig = (key: string, value: string) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const handleComplete = async () => {
    try {
      await api.put('/system/settings', config)
      navigate('/')
    } catch {
      alert('Setup failed')
    }
  }

  return (
    <div className="min-h-screen bg-bg-deep flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-xl">
          <h1 className="text-page-title text-accent-primary font-bold mb-2">MediaForge Setup</h1>
          <p className="text-body text-text-secondary">Get your media server configured in minutes</p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-xl">
          {steps.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-caption font-bold ${
                  i < step
                    ? 'bg-status-success text-white'
                    : i === step
                    ? 'bg-accent-primary text-white'
                    : 'bg-bg-elevated text-text-muted'
                }`}
              >
                {i < step ? <Check size={14} /> : i + 1}
              </div>
              {i < steps.length - 1 && (
                <div className={`w-8 h-0.5 ${i < step ? 'bg-status-success' : 'bg-bg-elevated'}`} />
              )}
            </div>
          ))}
        </div>

        <Card>
          <CardContent className="p-6">
            <h2 className="text-section-header mb-4">{steps[step].title}</h2>

            {step === 0 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-label text-text-secondary mb-1">Jellyfin URL</label>
                  <Input
                    placeholder="http://192.168.2.50:8096"
                    value={config.jellyfin_url}
                    onChange={(e) => updateConfig('jellyfin_url', e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-label text-text-secondary mb-1">API Key</label>
                  <Input
                    placeholder="Your Jellyfin API key"
                    value={config.jellyfin_api_key}
                    onChange={(e) => updateConfig('jellyfin_api_key', e.target.value)}
                  />
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-label text-text-secondary mb-1">Media Directory</label>
                  <Input value={config.media_dir} onChange={(e) => updateConfig('media_dir', e.target.value)} />
                </div>
                <div>
                  <label className="block text-label text-text-secondary mb-1">Download Directory</label>
                  <Input value={config.download_dir} onChange={(e) => updateConfig('download_dir', e.target.value)} />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-label text-text-secondary mb-1">VPN Provider</label>
                  <Input
                    placeholder="e.g., protonvpn, mullvad, airvpn"
                    value={config.vpn_provider}
                    onChange={(e) => updateConfig('vpn_provider', e.target.value)}
                  />
                </div>
                <p className="text-caption text-text-muted">
                  Upload your VPN config file to /config/vpn/ before connecting.
                </p>
              </div>
            )}

            {step === 3 && (
              <p className="text-body text-text-secondary">
                You can add indexers from the Indexers page after setup. Skip this step to get started quickly.
              </p>
            )}

            {step === 4 && (
              <p className="text-body text-text-secondary">
                TRaSH Guide recommended quality profiles will be loaded automatically. You can customize them later in Settings.
              </p>
            )}

            {step === 5 && (
              <div className="space-y-2">
                <p className="text-body text-text-secondary mb-4">Review your configuration:</p>
                {Object.entries(config)
                  .filter(([_, v]) => v)
                  .map(([key, value]) => (
                    <div key={key} className="flex justify-between text-body">
                      <span className="text-text-muted">{key.replace(/_/g, ' ')}</span>
                      <span className="text-text-primary">{key.includes('key') ? '***' : value}</span>
                    </div>
                  ))}
              </div>
            )}

            <div className="flex justify-between mt-6">
              <Button
                variant="secondary"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
              >
                Back
              </Button>
              {step < steps.length - 1 ? (
                <Button onClick={() => setStep((s) => s + 1)}>
                  Next <ChevronRight size={16} className="ml-1" />
                </Button>
              ) : (
                <Button onClick={handleComplete}>Launch MediaForge</Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
