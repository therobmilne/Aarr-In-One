import { useContext, useEffect } from 'react'
import { WebSocketContext } from '@/contexts/WebSocketContext'

export function useWebSocket(event: string, handler: (data: unknown) => void) {
  const ws = useContext(WebSocketContext)

  useEffect(() => {
    const unsubscribe = ws.subscribe(event, handler)
    return unsubscribe
  }, [ws, event, handler])
}
