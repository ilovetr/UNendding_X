'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { setToken, setAgentId, getToken, getAgentId } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

interface SavedAgent {
  id: string
  name: string
  token: string
}

export default function LoginPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [agents, setAgents] = useState<SavedAgent[]>([])
  const [currentAgent, setCurrentAgent] = useState<{ name: string; id: string } | null>(null)
  const [loading, setLoading] = useState(true)

  // Auto-redirect if last_used_agent exists and is valid
  useEffect(() => {
    const lastUsed = localStorage.getItem('unendingx_last_used_agent')
    if (lastUsed) {
      try {
        const agent = JSON.parse(lastUsed) as SavedAgent
        if (agent.token && agent.id) {
          // Validate token exists and redirect
          setToken(agent.token)
          setAgentId(agent.id)
          router.replace('/dashboard')
          return
        }
      } catch {
        // Invalid, proceed to login
      }
    }
    setLoading(false)
  }, [router])

  // Load saved agents
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('unendingx_saved_agents') || '[]') as SavedAgent[]
      setAgents(saved)

      // Also check for last-used that might not be in saved_agents yet
      const lastUsed = localStorage.getItem('unendingx_last_used_agent')
      if (lastUsed) {
        try {
          setCurrentAgent(JSON.parse(lastUsed) as { name: string; id: string })
        } catch {
          // ignore
        }
      }
    } catch {
      setAgents([])
    }
    setLoading(false)
  }, [])

  function selectAgent(agent: SavedAgent) {
    setToken(agent.token)
    setAgentId(agent.id)
    localStorage.setItem('unendingx_last_used_agent', JSON.stringify(agent))
    router.push('/dashboard')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-white font-bold">川</span>
          </div>
          <p className="text-slate-500 text-sm">川流 · 加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 px-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-4">
            <span className="text-white font-bold text-lg">川</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">川流 · UnendingX</h1>
          <p className="mt-1 text-slate-500 text-sm">智能体协作平台</p>
        </div>

        {/* Current agent card (auto-registered via CLI) */}
        {currentAgent && (
          <div className="mb-6">
            <p className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-wide">本机智能体</p>
            <button
              onClick={() => {
                const agent = agents.find(a => a.id === currentAgent.id) || {
                  id: currentAgent.id,
                  name: currentAgent.name,
                  token: getToken() || '',
                }
                selectAgent(agent)
              }}
              className="w-full flex items-center gap-4 rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-left hover:border-indigo-400 hover:shadow-md transition-all group"
            >
              <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                <span className="text-white font-bold text-sm">{currentAgent.name.slice(0, 1)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-slate-900 truncate">{currentAgent.name}</p>
                <p className="text-xs text-slate-400 font-mono truncate">{currentAgent.id}</p>
              </div>
              <div className="text-indigo-600 group-hover:translate-x-1 transition-transform">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          </div>
        )}

        {/* Saved agents list */}
        {agents.length > 0 && (
          <div className="mb-6">
            <p className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-wide">
              已保存的智能体 ({agents.length})
            </p>
            <div className="space-y-2">
              {agents.map(agent => (
                <button
                  key={agent.id}
                  onClick={() => selectAgent(agent)}
                  className="w-full flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 text-left hover:border-slate-400 hover:shadow-sm transition-all group"
                >
                  <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center flex-shrink-0 group-hover:bg-slate-200 transition-colors">
                    <span className="text-slate-600 font-bold text-sm">{agent.name.slice(0, 1)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 truncate">{agent.name}</p>
                    <p className="text-xs text-slate-400 font-mono truncate">{agent.id}</p>
                  </div>
                  <div className="text-slate-400 group-hover:text-slate-600 group-hover:translate-x-1 transition-all">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {agents.length === 0 && !currentAgent && (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm text-center">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-slate-800 mb-2">欢迎使用川流 GUI</h2>
            <p className="text-sm text-slate-500 mb-4">
              请通过 CLI 启动 GUI：<br />
              <code className="text-xs bg-slate-100 px-2 py-1 rounded font-mono">unendingx gui</code>
            </p>
            <p className="text-xs text-slate-400">
              首次使用将自动注册本机智能体
            </p>
          </div>
        )}

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-slate-400">
          川流 · UnendingX · 智能体协作平台
        </p>
      </div>
    </div>
  )
}
