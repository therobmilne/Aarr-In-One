type EventHandler = (data: unknown) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private listeners: Map<string, Set<EventHandler>> = new Map()
  private reconnectDelay = 1000
  private maxReconnectDelay = 30000
  private shouldReconnect = true

  connect() {
    const token = localStorage.getItem('mediaforge_token') || ''
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws?token=${token}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[WS] Connected')
      this.reconnectDelay = 1000
    }

    this.ws.onmessage = (event) => {
      try {
        const { event: eventType, data } = JSON.parse(event.data)
        const handlers = this.listeners.get(eventType)
        if (handlers) {
          handlers.forEach((handler) => handler(data))
        }
      } catch {
        // ignore parse errors
      }
    }

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay)
      }
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  subscribe(event: string, handler: EventHandler): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(handler)

    return () => {
      this.listeners.get(event)?.delete(handler)
    }
  }

  disconnect() {
    this.shouldReconnect = false
    this.ws?.close()
    this.ws = null
  }
}

export const wsClient = new WebSocketClient()
