'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { getToken } from './api'

const WS_RECONNECT_INTERVAL = 3000
const WS_MAX_RETRIES = 5

interface WebSocketMessage {
  type: string
  data?: any
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
}

interface UseWebSocketReturn {
  isConnected: boolean
  sendMessage: (type: string, data?: any) => void
  reconnect: () => void
}

export function useWebSocket(
  url: string,
  groupId: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn {
  const { onMessage, onConnect, onDisconnect, onError } = options

  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null)
  const pingInterval = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const token = getToken()
    if (!token) {
      console.warn('WebSocket: No token available')
      return
    }

    const wsUrl = `${url}/ws/groups/${groupId}?token=${token}`

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        reconnectAttempts.current = 0
        onConnect?.()

        // Start ping interval for heartbeat
        pingInterval.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage
          if (data.type === 'pong') {
            // Heartbeat response, ignore
            return
          }
          onMessage?.(data)
        } catch (err) {
          console.error('WebSocket: Failed to parse message', err)
        }
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason)
        setIsConnected(false)
        onDisconnect?.()

        // Clear ping interval
        if (pingInterval.current) {
          clearInterval(pingInterval.current)
          pingInterval.current = null
        }

        // Auto reconnect if not intentional close
        if (event.code !== 1000 && reconnectAttempts.current < WS_MAX_RETRIES) {
          reconnectAttempts.current++
          console.log(`WebSocket: Reconnecting (${reconnectAttempts.current}/${WS_MAX_RETRIES})...`)
          reconnectTimer.current = setTimeout(connect, WS_RECONNECT_INTERVAL)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        onError?.(error)
      }

      wsRef.current = ws
    } catch (err) {
      console.error('WebSocket: Failed to connect', err)
    }
  }, [url, groupId, onMessage, onConnect, onDisconnect, onError])

  const sendMessage = useCallback((type: string, data?: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }))
    } else {
      console.warn('WebSocket: Cannot send, not connected')
    }
  }, [])

  const reconnect = useCallback(() => {
    // Clear any existing reconnect timer
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close(1000, 'Reconnecting')
      wsRef.current = null
    }

    // Reset and reconnect
    reconnectAttempts.current = 0
    connect()
  }, [connect])

  // Connect on mount
  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
      if (pingInterval.current) {
        clearInterval(pingInterval.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount')
        wsRef.current = null
      }
    }
  }, [connect])

  return {
    isConnected,
    sendMessage,
    reconnect,
  }
}
