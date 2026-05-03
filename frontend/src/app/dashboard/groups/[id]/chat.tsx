'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useI18n } from '@/lib/i18n'
import {
  ChatMessage,
  fetchMessages,
  sendMessage,
  getMessagesByGroup,
  deleteRemoteMessage,
} from '@/lib/message-store'
import { ChatMessageList } from '@/components/chat-message'
import { MentionSelect } from '@/components/mention-select'
import { getToken, getAgentId, getAgentName, getAgentName as fetchAgentName } from '@/lib/api'
import { useWebSocket } from '@/lib/useWebSocket'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface GroupDetail {
  id: string
  name: string
  description: string
  owner_id: string
  members: Array<{
    agent_id: string
    agent_name: string
    role: string
  }>
}

interface DiscussionSetting {
  discussion_mode: boolean
  public_abilities: Array<{ id: string; name: string; access_level: string }>
  limited_abilities: Array<{ id: string; name: string; quota_remaining?: number }>
}

export default function GroupChatPage() {
  const params = useParams()
  const router = useRouter()
  const groupId = params.id as string
  const { t } = useI18n()

  const [group, setGroup] = useState<GroupDetail | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [showSidebar, setShowSidebar] = useState(false)
  const [discussionSetting, setDiscussionSetting] = useState<DiscussionSetting | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const wsMessageHandlerRef = useRef<(message: any) => void | null>(null)

  // WebSocket message handler
  const handleWSMessage = useCallback((message: any) => {
    if (message.type === 'new_message' && message.data) {
      const msg = message.data
      // Only add if not from current user (current user already added via sendMessage)
      const currentAgentId = getAgentId()
      if (msg.sender?.id !== currentAgentId) {
        setMessages(prev => {
          // Check if message already exists
          if (prev.some(m => m.id === msg.id)) {
            return prev
          }
          const newMsg: ChatMessage = {
            id: msg.id,
            group_id: groupId,
            sender: {
              type: msg.sender?.type || 'agent',
              id: msg.sender?.id || '',
              name: msg.sender?.name || 'Unknown',
            },
            content: msg.content,
            timestamp: msg.timestamp ? new Date(msg.timestamp).getTime() : Date.now(),
            mentions: msg.mentions || [],
            is_broadcast: msg.is_broadcast || false,
            is_a2a_triggered: msg.is_a2a_triggered || false,
            a2a_response_to: msg.a2a_response_to || null,
            direction: 'incoming',
          }
          return [...prev, newMsg]
        })
      }
    }
  }, [groupId])

  // Initialize WebSocket
  const { isConnected: wsConnected } = useWebSocket(API_BASE.replace('http', 'ws').replace('https', 'wss'), groupId, {
    onMessage: handleWSMessage,
    onConnect: () => console.log('Group chat WebSocket connected'),
    onDisconnect: () => console.log('Group chat WebSocket disconnected'),
  })

  // Fetch group details
  const fetchGroup = useCallback(async () => {
    const token = getToken()
    try {
      const res = await fetch(`${API_BASE}/api/groups/${groupId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to fetch group')
      const data = await res.json()
      setGroup(data)
    } catch (err) {
      console.error('Error fetching group:', err)
    }
  }, [groupId])

  // Fetch messages
  const loadMessages = useCallback(async () => {
    try {
      // First load from IndexedDB
      const cached = await getMessagesByGroup(groupId, { limit: 50 })
      if (cached.length > 0) {
        setMessages(cached.sort((a, b) => a.timestamp - b.timestamp))
      }

      // Then fetch from API
      const fresh = await fetchMessages(groupId, { limit: 50 })
      setMessages(fresh.sort((a, b) => a.timestamp - b.timestamp))
    } catch (err) {
      console.error('Error loading messages:', err)
    } finally {
      setLoading(false)
    }
  }, [groupId])

  // Fetch discussion settings
  const fetchDiscussionSettings = useCallback(async () => {
    const token = getToken()
    try {
      const res = await fetch(`${API_BASE}/api/groups/${groupId}/messages/discussion`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setDiscussionSetting(data)
      }
    } catch (err) {
      console.error('Error fetching discussion settings:', err)
    }
  }, [groupId])

  // Initial load
  useEffect(() => {
    if (!groupId) return
    Promise.all([fetchGroup(), loadMessages(), fetchDiscussionSettings()])
  }, [groupId, fetchGroup, loadMessages, fetchDiscussionSettings])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle send message
  const handleSend = async () => {
    if (!inputValue.trim() || sending) return

    const content = inputValue.trim()
    setInputValue('')
    setSending(true)

    // Extract mentions
    const mentions: string[] = []
    const atAllMention = content.match(/@all/gi)
    if (atAllMention) {
      mentions.push('@all')
    }

    // Extract @name mentions
    const nameMentions = content.match(/@(\S+)/g)
    if (nameMentions && group) {
      nameMentions.forEach(mention => {
        const name = mention.slice(1).toLowerCase()
        const member = group.members.find(m =>
          m.agent_name.toLowerCase() === name
        )
        if (member && !mentions.includes(member.agent_id)) {
          mentions.push(member.agent_id)
        }
      })
    }

    try {
      const msg = await sendMessage(
        groupId,
        content,
        mentions,
        mentions.includes('@all'),
        fetchAgentName() || 'User'
      )
      setMessages(prev => [...prev, msg])
    } catch (err) {
      console.error('Error sending message:', err)
      alert('发送失败，请重试')
    } finally {
      setSending(false)
    }
  }

  // Handle delete message
  const handleDelete = async (messageId: string) => {
    if (!confirm('确定删除这条消息？')) return

    try {
      await deleteRemoteMessage(groupId, messageId)
      setMessages(prev => prev.filter(m => m.id !== messageId))
    } catch (err) {
      console.error('Error deleting message:', err)
    }
  }

  // Toggle discussion mode
  const toggleDiscussionMode = async () => {
    const token = getToken()
    const newValue = !discussionSetting?.discussion_mode

    try {
      const res = await fetch(`${API_BASE}/api/groups/${groupId}/messages/discussion`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ discussion_mode: newValue }),
      })

      if (res.ok) {
        const data = await res.json()
        setDiscussionSetting(data)
      }
    } catch (err) {
      console.error('Error updating discussion mode:', err)
    }
  }

  if (loading && !group) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-400">{t('chat.loading') || '加载中...'}</div>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] bg-white rounded-2xl border border-slate-200 overflow-hidden">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/dashboard/groups')}
              className="p-2 hover:bg-slate-200 rounded-lg transition"
            >
              <svg className="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div>
              <h2 className="text-lg font-bold text-slate-800">{group?.name}</h2>
              <p className="text-xs text-slate-500">
                {group?.members.length || 0} {t('chat.members') || '位成员'}
              </p>
            </div>
            {/* WebSocket connection indicator */}
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-slate-300'}`} title={wsConnected ? '实时连接已建立' : '实时连接未建立'} />
          </div>

          <div className="flex items-center gap-2">
            {/* Discussion mode indicator */}
            {discussionSetting && (
              <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                discussionSetting.discussion_mode
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-500'
              }`}>
                {discussionSetting.discussion_mode
                  ? t('chat.discussionOn') || '讨论模式已开启'
                  : t('chat.discussionOff') || '讨论模式已关闭'
                }
              </div>
            )}

            {/* Settings button */}
            <button
              onClick={() => setShowSidebar(v => !v)}
              className={`p-2 rounded-lg transition ${
                showSidebar ? 'bg-indigo-100 text-indigo-600' : 'hover:bg-slate-200 text-slate-600'
              }`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Messages */}
        <div ref={containerRef} className="flex-1 overflow-hidden">
          <ChatMessageList
            messages={messages}
            onDelete={handleDelete}
            loading={loading}
          />
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-4 border-t border-slate-200 bg-white">
          <MentionSelect
            members={group?.members || []}
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            disabled={sending}
          />
        </div>
      </div>

      {/* Sidebar */}
      {showSidebar && (
        <div className="w-72 border-l border-slate-200 bg-slate-50 overflow-y-auto">
          {/* Members */}
          <div className="p-4">
            <h3 className="text-sm font-semibold text-slate-800 mb-3">
              {t('chat.members') || '群组成员'}
            </h3>
            <div className="space-y-2">
              {group?.members.map(member => (
                <div
                  key={member.agent_id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-white transition"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    member.role === 'admin'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-indigo-100 text-indigo-700'
                  }`}>
                    {member.agent_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">
                      {member.agent_name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {member.role === 'admin' ? t('chat.admin') || '管理员' : t('chat.member') || '成员'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="border-t border-slate-200" />

          {/* Ability settings */}
          <div className="p-4">
            <h3 className="text-sm font-semibold text-slate-800 mb-3">
              {t('chat.abilitySettings') || '能力开放设置'}
            </h3>

            {/* Discussion mode toggle */}
            <div className="mb-4">
              <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {t('chat.discussionMode') || '讨论模式'}
                  </p>
                  <p className="text-xs text-slate-400">
                    {t('chat.discussionModeDesc') || '接收群组广播和@消息'}
                  </p>
                </div>
                <button
                  onClick={toggleDiscussionMode}
                  className={`w-12 h-6 rounded-full transition relative ${
                    discussionSetting?.discussion_mode
                      ? 'bg-emerald-500'
                      : 'bg-slate-300'
                  }`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition ${
                    discussionSetting?.discussion_mode
                      ? 'left-7'
                      : 'left-1'
                  }`} />
                </button>
              </div>
            </div>

            {/* Public abilities */}
            <div className="mb-4">
              <p className="text-xs font-medium text-slate-500 mb-2">
                {t('chat.publicAbilities') || '公共服务'}
              </p>
              <div className="space-y-1">
                {discussionSetting?.public_abilities.length ? (
                  discussionSetting.public_abilities.map((ability: any) => (
                    <div key={ability.id} className="px-3 py-2 bg-white rounded-lg border border-slate-200">
                      <p className="text-sm text-slate-700">{ability.name}</p>
                      <p className="text-xs text-slate-400">{ability.access_level}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">{t('chat.noPublicAbilities') || '暂无'}</p>
                )}
              </div>
            </div>

            {/* Limited abilities */}
            <div>
              <p className="text-xs font-medium text-slate-500 mb-2">
                {t('chat.limitedAbilities') || '受限能力'}
              </p>
              <div className="space-y-1">
                {discussionSetting?.limited_abilities.length ? (
                  discussionSetting.limited_abilities.map((ability: any) => (
                    <div key={ability.id} className="px-3 py-2 bg-white rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-slate-700">{ability.name}</p>
                        {ability.quota_remaining !== undefined && (
                          <span className="text-xs text-slate-400">
                            {ability.quota_remaining} {t('chat.quotaLeft') || '次'}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">{t('chat.noLimitedAbilities') || '暂无'}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
