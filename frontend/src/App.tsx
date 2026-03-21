import { useEffect, useState } from 'react'
import { RouterProvider } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { WebSocketProvider } from '@/contexts/WebSocketContext'
import { router } from '@/router'
import api from '@/lib/api'

export default function App() {
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const checkSetup = async () => {
      try {
        const { data } = await api.get('/setup/status')
        if (!data.is_complete && window.location.pathname !== '/setup') {
          window.location.href = '/setup'
          return
        }
      } catch {
        // API not ready, just show the app
      }
      setChecking(false)
    }
    checkSetup()
  }, [])

  if (checking) {
    return (
      <div className="min-h-screen bg-bg-deep flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-accent-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-text-secondary text-body">Loading MediaForge...</p>
        </div>
      </div>
    )
  }

  return (
    <AuthProvider>
      <WebSocketProvider>
        <RouterProvider router={router} />
      </WebSocketProvider>
    </AuthProvider>
  )
}
