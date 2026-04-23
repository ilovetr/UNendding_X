'use client'

import { getToken, getAgentId } from './api'

const DB_NAME = 'unendingx_messages'
const DB_VERSION = 1
const STORE_NAME = 'messages'
const INDEX_GROUP_ID = 'by_group_id'
const INDEX_TIMESTAMP = 'by_timestamp'

export interface ChatMessage {
  id: string
  group_id: string
  sender: {
    type: 'agent' | 'human'
    id: string
    name: string
  }
  content: string
  mentions: string[]
  is_broadcast: boolean
  is_a2a_triggered: boolean
  a2a_response_to: string | null
  timestamp: number
  direction: 'outgoing' | 'incoming'
  status?: 'sending' | 'sent' | 'error'
}

let dbInstance: IDBDatabase | null = null

function openDB(): Promise<IDBDatabase> {
  if (dbInstance) return Promise.resolve(dbInstance)

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      dbInstance = request.result
      resolve(dbInstance)
    }

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result

      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        store.createIndex(INDEX_GROUP_ID, 'group_id', { unique: false })
        store.createIndex(INDEX_TIMESTAMP, 'timestamp', { unique: false })
      }
    }
  })
}

export async function saveMessage(message: ChatMessage): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).put(message)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function saveMessages(messages: ChatMessage[]): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    messages.forEach(msg => store.put(msg))
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function getMessagesByGroup(
  groupId: string,
  options?: { beforeTimestamp?: number; limit?: number }
): Promise<ChatMessage[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const index = store.index(INDEX_GROUP_ID)
    const messages: ChatMessage[] = []

    const request = index.getAll(groupId)

    request.onsuccess = () => {
      let results = request.result as ChatMessage[]

      // Filter by timestamp if provided
      if (options?.beforeTimestamp) {
        results = results.filter(m => m.timestamp < options.beforeTimestamp!)
      }

      // Sort by timestamp descending
      results.sort((a, b) => b.timestamp - a.timestamp)

      // Apply limit
      if (options?.limit) {
        results = results.slice(0, options.limit)
      }

      resolve(results)
    }

    request.onerror = () => reject(request.error)
  })
}

export async function deleteMessage(id: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    tx.objectStore(STORE_NAME).delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function deleteOldMessages(daysOld: number = 30): Promise<void> {
  const db = await openDB()
  const cutoff = Date.now() - daysOld * 24 * 60 * 60 * 1000

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const request = store.openCursor()

    request.onsuccess = () => {
      const cursor = request.result
      if (cursor) {
        if (cursor.value.timestamp < cutoff) {
          cursor.delete()
        }
        cursor.continue()
      }
    }

    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

// ── API Integration ───────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchMessages(
  groupId: string,
  options?: { skip?: number; limit?: number; beforeTimestamp?: string }
): Promise<ChatMessage[]> {
  const token = getToken()
  const agentId = getAgentId()

  const params = new URLSearchParams()
  if (options?.skip) params.set('skip', String(options.skip))
  if (options?.limit) params.set('limit', String(options.limit || 50))
  if (options?.beforeTimestamp) params.set('before_timestamp', options.beforeTimestamp)

  const response = await fetch(
    `${API_BASE}/api/groups/${groupId}/messages?${params}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch messages: ${response.statusText}`)
  }

  const messages = await response.json()

  // Add direction and save to IndexedDB
  const enrichedMessages: ChatMessage[] = messages.map((msg: any) => {
    const isOwn = msg.sender.id === agentId
    return {
      ...msg,
      timestamp: new Date(msg.timestamp).getTime(),
      direction: isOwn ? 'outgoing' : 'incoming',
    } as ChatMessage
  })

  // Cache to IndexedDB
  await saveMessages(enrichedMessages)

  return enrichedMessages
}

export async function sendMessage(
  groupId: string,
  content: string,
  mentions: string[] = [],
  isBroadcast: boolean = false,
  senderName: string = 'User'
): Promise<ChatMessage> {
  const token = getToken()
  const agentId = getAgentId()

  const tempId = `temp_${Date.now()}`
  const tempMessage: ChatMessage = {
    id: tempId,
    group_id: groupId,
    sender: {
      type: 'human',
      id: agentId,
      name: senderName,
    },
    content,
    mentions,
    is_broadcast: isBroadcast,
    is_a2a_triggered: false,
    a2a_response_to: null,
    timestamp: Date.now(),
    direction: 'outgoing',
    status: 'sending',
  }

  // Save locally first
  await saveMessage(tempMessage)

  try {
    const response = await fetch(`${API_BASE}/api/groups/${groupId}/messages`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sender: {
          type: 'human',
          id: agentId,
          name: senderName,
        },
        content,
        mentions,
        is_broadcast: isBroadcast,
      }),
    })

    if (!response.ok) {
      throw new Error(`Failed to send message: ${response.statusText}`)
    }

    const savedMessage = await response.json()

    // Replace temp message with real one
    const finalMessage: ChatMessage = {
      ...savedMessage,
      timestamp: new Date(savedMessage.timestamp).getTime(),
      direction: 'outgoing',
      status: 'sent',
    } as ChatMessage

    await deleteMessage(tempId)
    await saveMessage(finalMessage)

    return finalMessage
  } catch (error) {
    // Mark temp message as error
    const errorMessage: ChatMessage = {
      ...tempMessage,
      status: 'error',
    }
    await saveMessage(errorMessage)
    throw error
  }
}

export async function deleteRemoteMessage(
  groupId: string,
  messageId: string
): Promise<void> {
  const token = getToken()

  const response = await fetch(
    `${API_BASE}/api/groups/${groupId}/messages/${messageId}`,
    {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  )

  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete message: ${response.statusText}`)
  }

  // Remove from IndexedDB
  await deleteMessage(messageId)
}
