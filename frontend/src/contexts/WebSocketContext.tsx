import { createContext, useEffect, type ReactNode } from 'react'
import { wsClient } from '@/lib/ws'

export const WebSocketContext = createContext(wsClient)

export function WebSocketProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const token = localStorage.getItem('mediaforge_token')
    if (token) {
      wsClient.connect()
    }
    return () => wsClient.disconnect()
  }, [])

  return (
    <WebSocketContext.Provider value={wsClient}>{children}</WebSocketContext.Provider>
  )
}
