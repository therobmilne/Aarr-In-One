import { useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/shared/EmptyState'
import { Home } from 'lucide-react'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <EmptyState
      icon={Home}
      title="Page not found"
      description="The page you're looking for doesn't exist or has been moved."
      action={{ label: 'Go Home', onClick: () => navigate('/') }}
    />
  )
}
