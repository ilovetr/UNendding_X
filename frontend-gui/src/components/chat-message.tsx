'use client'

import { ChatMessage } from '@/lib/message-store'
import { format } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'
import { useI18n } from '@/lib/i18n'

interface ChatMessageProps {
  message: ChatMessage
  onDelete?: (id: string) => void
  showAvatar?: boolean
}

export function ChatMessageBubble({ message, onDelete, showAvatar = true }: ChatMessageProps) {
  const { locale } = useI18n()
  const isOutgoing = message.direction === 'outgoing'
  const isAgent = message.sender.type === 'agent'

  const formatTime = (ts: number) => {
    const date = new Date(ts)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()

    if (isToday) {
      return format(date, 'HH:mm')
    }
    return format(date, 'MM/dd HH:mm', { locale: locale === 'zh' ? zhCN : enUS })
  }

  return (
    <div className={`flex gap-3 ${isOutgoing ? 'flex-row-reverse' : ''} animate-fade-in`}>
      {/* Avatar */}
      {showAvatar && (
        <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold ${
          isAgent
            ? 'bg-indigo-100 text-indigo-700'
            : 'bg-emerald-100 text-emerald-700'
        }`}>
          {message.sender.name.charAt(0).toUpperCase()}
        </div>
      )}

      {/* Message content */}
      <div className={`max-w-[70%] ${isOutgoing ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        {/* Sender name */}
        <div className={`flex items-center gap-2 text-xs ${isOutgoing ? 'flex-row-reverse' : ''}`}>
          <span className={`font-medium ${isAgent ? 'text-indigo-600' : 'text-emerald-600'}`}>
            {message.sender.name}
          </span>
          {message.is_broadcast && (
            <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[10px] rounded">
              @{isOutgoing ? '你' : 'all'}
            </span>
          )}
          {message.is_a2a_triggered && (
            <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-[10px] rounded">
              A2A
            </span>
          )}
          <span className="text-slate-400">{formatTime(message.timestamp)}</span>
        </div>

        {/* Message bubble */}
        <div
          className={`relative px-4 py-2.5 rounded-2xl ${
            isOutgoing
              ? 'bg-indigo-600 text-white rounded-br-md'
              : 'bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-sm'
          }`}
        >
          {/* Mentions highlight */}
          {message.mentions.length > 0 && !message.is_broadcast && (
            <div className="mb-1 flex flex-wrap gap-1">
              {message.mentions.map((mention, i) => (
                <span key={i} className={`text-xs px-1.5 py-0.5 rounded ${
                  isOutgoing ? 'bg-indigo-500 text-indigo-100' : 'bg-slate-100 text-slate-600'
                }`}>
                  @{mention}
                </span>
              ))}
            </div>
          )}

          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </p>

          {/* Status indicator for outgoing messages */}
          {isOutgoing && (
            <div className="absolute -bottom-1 right-2">
              {message.status === 'sending' && (
                <div className="w-4 h-4 flex items-center justify-center">
                  <div className="w-2 h-2 bg-white/50 rounded-full animate-pulse" />
                </div>
              )}
              {message.status === 'error' && (
                <button
                  onClick={() => onDelete?.(message.id)}
                  className="w-4 h-4 flex items-center justify-center bg-red-500 text-white rounded-full text-[10px]"
                  title="重试"
                >
                  !
                </button>
              )}
              {message.status === 'sent' && (
                <div className="w-4 h-4 flex items-center justify-center text-white/50">
                  ✓
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface ChatMessageListProps {
  messages: ChatMessage[]
  onDelete?: (id: string) => void
  loading?: boolean
}

export function ChatMessageList({ messages, onDelete, loading }: ChatMessageListProps) {
  const { t } = useI18n()

  if (loading && messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-slate-400">{t('chat.loading') || '加载中...'}</div>
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-2">💬</div>
          <p className="text-slate-400">{t('chat.empty') || '暂无消息，开始聊天吧'}</p>
        </div>
      </div>
    )
  }

  // Group messages by date
  const groupedMessages: { date: string; messages: ChatMessage[] }[] = []
  let currentDate = ''

  messages.forEach(msg => {
    const msgDate = new Date(msg.timestamp).toDateString()
    if (msgDate !== currentDate) {
      currentDate = msgDate
      groupedMessages.push({ date: currentDate, messages: [] })
    }
    groupedMessages[groupedMessages.length - 1].messages.push(msg)
  })

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
      {groupedMessages.map(group => (
        <div key={group.date}>
          {/* Date divider */}
          <div className="flex items-center justify-center my-4">
            <div className="px-3 py-1 bg-slate-100 rounded-full text-xs text-slate-500">
              {format(new Date(group.date), 'yyyy年M月d日', { locale: zhCN })}
            </div>
          </div>

          {/* Messages */}
          <div className="space-y-4">
            {group.messages.map((msg, i) => {
              // Show avatar only when sender changes or time gap > 5min
              const prevMsg = i > 0 ? group.messages[i - 1] : null
              const showAvatar = !prevMsg ||
                prevMsg.sender.id !== msg.sender.id ||
                msg.timestamp - prevMsg.timestamp > 5 * 60 * 1000

              return (
                <ChatMessageBubble
                  key={msg.id}
                  message={msg}
                  onDelete={onDelete}
                  showAvatar={showAvatar}
                />
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
