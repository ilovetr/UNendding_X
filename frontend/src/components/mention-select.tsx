'use client'

import { useState, useRef, useEffect } from 'react'
import { useI18n } from '@/lib/i18n'

interface GroupMember {
  agent_id: string
  agent_name: string
  role: string
}

interface MentionSelectProps {
  members: GroupMember[]
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
  placeholder?: string
}

export function MentionSelect({
  members,
  value,
  onChange,
  onSend,
  disabled,
  placeholder,
}: MentionSelectProps) {
  const [showMentions, setShowMentions] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { t } = useI18n()

  // Filter members based on query
  const filteredMembers = members.filter(m =>
    m.agent_name.toLowerCase().includes(mentionQuery.toLowerCase())
  )

  // Handle @ trigger
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value
    onChange(newValue)

    // Detect @ trigger
    const cursorPos = e.target.selectionStart
    const textBeforeCursor = newValue.slice(0, cursorPos)
    const atMatch = textBeforeCursor.match(/@(\w*)$/)

    if (atMatch) {
      setShowMentions(true)
      setMentionQuery(atMatch[1])
    } else {
      setShowMentions(false)
    }
  }

  // Handle mention selection
  const selectMention = (member: GroupMember) => {
    const cursorPos = inputRef.current?.selectionStart || 0
    const textBeforeCursor = value.slice(0, cursorPos)
    const textAfterCursor = value.slice(cursorPos)

    // Replace @query with @member_name
    const atIndex = textBeforeCursor.lastIndexOf('@')
    const newValue =
      textBeforeCursor.slice(0, atIndex) +
      `@${member.agent_name} ` +
      textAfterCursor

    onChange(newValue)
    setShowMentions(false)

    // Focus back on input
    setTimeout(() => {
      inputRef.current?.focus()
    }, 0)
  }

  // Handle keyboard
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !showMentions) {
      e.preventDefault()
      onSend()
    }

    if (e.key === 'Escape') {
      setShowMentions(false)
    }
  }

  // Close mentions on click outside
  useEffect(() => {
    const handleClickOutside = () => setShowMentions(false)
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  return (
    <div className="relative">
      {/* Input area */}
      <div className="flex items-end gap-2 bg-white border border-slate-200 rounded-2xl px-4 py-3">
        {/* Mention button */}
        <button
          onClick={() => {
            setShowMentions(v => !v)
            setMentionQuery('')
          }}
          className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 transition"
          title="@提及成员"
        >
          <span className="text-lg">@</span>
        </button>

        {/* Text input */}
        <textarea
          ref={inputRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder || t('chat.placeholder') || '输入消息...'}
          className="flex-1 min-h-[24px] max-h-32 resize-none bg-transparent border-none outline-none text-sm placeholder-slate-400"
          rows={1}
        />

        {/* Send button */}
        <button
          onClick={onSend}
          disabled={disabled || !value.trim()}
          className={`flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full transition ${
            value.trim() && !disabled
              ? 'bg-indigo-600 text-white hover:bg-indigo-700'
              : 'bg-slate-100 text-slate-400'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>

      {/* @ mentions dropdown */}
      {showMentions && (
        <div
          className="absolute bottom-full left-0 mb-2 w-64 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden z-50"
          onClick={e => e.stopPropagation()}
        >
          {/* @all option */}
          <button
            onClick={() => {
              const cursorPos = inputRef.current?.selectionStart || 0
              const textBeforeCursor = value.slice(0, cursorPos)
              const atIndex = textBeforeCursor.lastIndexOf('@')
              const newValue =
                textBeforeCursor.slice(0, atIndex) +
                '@all ' +
                value.slice(cursorPos)
              onChange(newValue)
              setShowMentions(false)
              inputRef.current?.focus()
            }}
            className="w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-50 transition text-left"
          >
            <div className="w-8 h-8 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center text-sm font-bold">
              @
            </div>
            <div>
              <p className="text-sm font-medium text-slate-800">{t('chat.atAll') || '@所有人'}</p>
              <p className="text-xs text-slate-400">{t('chat.atAllDesc') || '广播给所有成员'}</p>
            </div>
          </button>

          <div className="border-t border-slate-100" />

          {/* Members list */}
          {filteredMembers.length === 0 ? (
            <div className="px-4 py-3 text-sm text-slate-400">
              {t('chat.noMembers') || '没有找到成员'}
            </div>
          ) : (
            filteredMembers.map(member => (
              <button
                key={member.agent_id}
                onClick={() => selectMention(member)}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-50 transition text-left"
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  member.role === 'admin'
                    ? 'bg-purple-100 text-purple-700'
                    : 'bg-indigo-100 text-indigo-700'
                }`}>
                  {member.agent_name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{member.agent_name}</p>
                  <p className="text-xs text-slate-400">
                    {member.role === 'admin' ? t('chat.admin') || '管理员' : t('chat.member') || '成员'}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
