import { useEffect, useState } from 'react'
import { Subtitles, Plus, Pencil, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/EmptyState'
import api from '@/lib/api'

interface SubtitleProfile {
  id: number
  name: string
  languages: string[]
  min_score: number
  providers: string[]
  hearing_impaired: boolean
  auto_download: boolean
  auto_upgrade: boolean
  preferred_format: string
  is_default: boolean
}

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'lt', label: 'Lithuanian' },
  { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' },
  { code: 'de', label: 'German' },
  { code: 'pt', label: 'Portuguese' },
  { code: 'it', label: 'Italian' },
  { code: 'nl', label: 'Dutch' },
  { code: 'pl', label: 'Polish' },
  { code: 'ru', label: 'Russian' },
  { code: 'ar', label: 'Arabic' },
  { code: 'zh', label: 'Chinese' },
  { code: 'ja', label: 'Japanese' },
  { code: 'ko', label: 'Korean' },
]

const PROVIDERS = [
  { id: 'opensubtitles', label: 'OpenSubtitles' },
  { id: 'addic7ed', label: 'Addic7ed' },
  { id: 'podnapisi', label: 'Podnapisi' },
  { id: 'subscenter', label: 'Subscenter' },
  { id: 'legendastv', label: 'LegendasTV' },
]

const FORMATS = ['srt', 'ass', 'sub']

interface FormState {
  name: string
  languages: string[]
  hearing_impaired: boolean
  min_score: number
  providers: string[]
  auto_download: boolean
  auto_upgrade: boolean
  preferred_format: string
  is_default: boolean
}

const defaultForm: FormState = {
  name: '',
  languages: ['en'],
  hearing_impaired: false,
  min_score: 70,
  providers: ['opensubtitles'],
  auto_download: true,
  auto_upgrade: true,
  preferred_format: 'srt',
  is_default: false,
}

export function SubtitlesPage() {
  const [profiles, setProfiles] = useState<SubtitleProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<FormState>({ ...defaultForm })
  const [saving, setSaving] = useState(false)

  const fetchProfiles = async () => {
    try {
      const { data } = await api.get('/subtitles/profiles')
      setProfiles(Array.isArray(data) ? data : [])
    } catch {
      // Not ready
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfiles()
  }, [])

  const openCreateForm = () => {
    setForm({ ...defaultForm })
    setEditingId(null)
    setShowForm(true)
  }

  const openEditForm = (profile: SubtitleProfile) => {
    setForm({
      name: profile.name,
      languages: [...profile.languages],
      hearing_impaired: profile.hearing_impaired,
      min_score: profile.min_score,
      providers: [...profile.providers],
      auto_download: profile.auto_download,
      auto_upgrade: profile.auto_upgrade,
      preferred_format: profile.preferred_format,
      is_default: profile.is_default,
    })
    setEditingId(profile.id)
    setShowForm(true)
  }

  const cancelForm = () => {
    setShowForm(false)
    setEditingId(null)
    setForm({ ...defaultForm })
  }

  const toggleLanguage = (code: string) => {
    setForm((prev) => ({
      ...prev,
      languages: prev.languages.includes(code)
        ? prev.languages.filter((l) => l !== code)
        : [...prev.languages, code],
    }))
  }

  const toggleProvider = (id: string) => {
    setForm((prev) => ({
      ...prev,
      providers: prev.providers.includes(id)
        ? prev.providers.filter((p) => p !== id)
        : [...prev.providers, id],
    }))
  }

  const handleSave = async () => {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      if (editingId !== null) {
        await api.put(`/subtitles/profiles/${editingId}`, form)
      } else {
        await api.post('/subtitles/profiles', form)
      }
      await fetchProfiles()
      cancelForm()
    } catch (err) {
      console.error('Failed to save profile', err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/subtitles/profiles/${id}`)
      setProfiles((prev) => prev.filter((p) => p.id !== id))
      if (editingId === id) {
        cancelForm()
      }
    } catch (err) {
      console.error('Failed to delete profile', err)
    }
  }

  const renderForm = () => (
    <Card className="mt-4">
      <CardContent className="p-6 space-y-5">
        <h3 className="text-card-title text-text-primary">
          {editingId !== null ? 'Edit Profile' : 'New Profile'}
        </h3>

        {/* Profile Name */}
        <div>
          <label className="block text-caption text-text-secondary mb-1">Profile Name</label>
          <Input
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="e.g. English + Lithuanian"
          />
        </div>

        {/* Languages */}
        <div>
          <label className="block text-caption text-text-secondary mb-2">Languages</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-2">
            {LANGUAGES.map((lang) => (
              <label
                key={lang.code}
                className="flex items-center gap-2 cursor-pointer text-body text-text-primary"
              >
                <input
                  type="checkbox"
                  checked={form.languages.includes(lang.code)}
                  onChange={() => toggleLanguage(lang.code)}
                  className="accent-accent-primary w-4 h-4"
                />
                {lang.label}
              </label>
            ))}
          </div>
        </div>

        {/* Hearing Impaired */}
        <div className="flex items-center gap-3">
          <label className="text-caption text-text-secondary">Hearing Impaired</label>
          <button
            type="button"
            onClick={() => setForm((f) => ({ ...f, hearing_impaired: !f.hearing_impaired }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              form.hearing_impaired ? 'bg-accent-primary' : 'bg-bg-elevated'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                form.hearing_impaired ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Minimum Score */}
        <div>
          <label className="block text-caption text-text-secondary mb-1">Minimum Score</label>
          <Input
            type="number"
            min={0}
            max={100}
            value={form.min_score}
            onChange={(e) =>
              setForm((f) => ({ ...f, min_score: Math.min(100, Math.max(0, Number(e.target.value))) }))
            }
            className="w-32"
          />
        </div>

        {/* Providers */}
        <div>
          <label className="block text-caption text-text-secondary mb-2">Providers</label>
          <div className="flex flex-wrap gap-4">
            {PROVIDERS.map((prov) => (
              <label
                key={prov.id}
                className="flex items-center gap-2 cursor-pointer text-body text-text-primary"
              >
                <input
                  type="checkbox"
                  checked={form.providers.includes(prov.id)}
                  onChange={() => toggleProvider(prov.id)}
                  className="accent-accent-primary w-4 h-4"
                />
                {prov.label}
              </label>
            ))}
          </div>
        </div>

        {/* Auto-Download */}
        <div className="flex items-center gap-3">
          <label className="text-caption text-text-secondary">Auto-Download</label>
          <button
            type="button"
            onClick={() => setForm((f) => ({ ...f, auto_download: !f.auto_download }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              form.auto_download ? 'bg-accent-primary' : 'bg-bg-elevated'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                form.auto_download ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Auto-Upgrade */}
        <div className="flex items-center gap-3">
          <label className="text-caption text-text-secondary">Auto-Upgrade</label>
          <button
            type="button"
            onClick={() => setForm((f) => ({ ...f, auto_upgrade: !f.auto_upgrade }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              form.auto_upgrade ? 'bg-accent-primary' : 'bg-bg-elevated'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                form.auto_upgrade ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Preferred Format */}
        <div>
          <label className="block text-caption text-text-secondary mb-1">Preferred Format</label>
          <select
            value={form.preferred_format}
            onChange={(e) => setForm((f) => ({ ...f, preferred_format: e.target.value }))}
            className="h-10 rounded-sm border border-bg-elevated bg-bg-surface px-3 py-2 text-body text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary"
          >
            {FORMATS.map((fmt) => (
              <option key={fmt} value={fmt}>
                {fmt}
              </option>
            ))}
          </select>
        </div>

        {/* Set as Default */}
        <div className="flex items-center gap-3">
          <label className="text-caption text-text-secondary">Set as Default</label>
          <button
            type="button"
            onClick={() => setForm((f) => ({ ...f, is_default: !f.is_default }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              form.is_default ? 'bg-accent-primary' : 'bg-bg-elevated'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                form.is_default ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <Button onClick={handleSave} disabled={saving || !form.name.trim()}>
            {saving ? 'Saving...' : editingId !== null ? 'Update Profile' : 'Save Profile'}
          </Button>
          <Button variant="secondary" onClick={cancelForm}>
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  )

  return (
    <div>
      <PageHeader title="Subtitles" subtitle="Language profiles and providers">
        <Button onClick={openCreateForm}>
          <Plus size={16} className="mr-1" /> Add Profile
        </Button>
      </PageHeader>

      {showForm && renderForm()}

      {profiles.length === 0 && !showForm ? (
        <EmptyState
          icon={Subtitles}
          title="No subtitle profiles configured"
          description="Create a language profile to automatically download subtitles for your media."
          action={{ label: 'Create Profile', onClick: openCreateForm }}
        />
      ) : (
        <div className="space-y-3 mt-4">
          {profiles.map((p) => (
            <Card key={p.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-body font-medium">{p.name}</span>
                      {p.is_default && <Badge variant="healthy">Default</Badge>}
                      {p.hearing_impaired && <Badge>HI</Badge>}
                      {p.auto_download && <Badge>Auto</Badge>}
                      {p.auto_upgrade && <Badge>Upgrade</Badge>}
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-caption text-text-muted flex-wrap">
                      <span>
                        Languages:{' '}
                        {p.languages
                          .map((code) => LANGUAGES.find((l) => l.code === code)?.label || code)
                          .join(', ')}
                      </span>
                      <span>Min Score: {p.min_score}%</span>
                      <span>
                        Providers:{' '}
                        {p.providers
                          .map((id) => PROVIDERS.find((pr) => pr.id === id)?.label || id)
                          .join(', ')}
                      </span>
                      <span>Format: {p.preferred_format}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4 shrink-0">
                    <Button variant="ghost" size="sm" onClick={() => openEditForm(p)}>
                      <Pencil size={14} className="mr-1" /> Edit
                    </Button>
                    <Button variant="destructive" size="sm" onClick={() => handleDelete(p.id)}>
                      <Trash2 size={14} className="mr-1" /> Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
