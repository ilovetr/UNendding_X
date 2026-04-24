'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { clearAuth, getAgentId, setAgentId, setToken, getToken } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { useEffect, useState } from 'react'

interface SavedAgent {
  id: string
  name: string
  token: string
}

const NAV_KEYS = [
  { href: '/dashboard', labelKey: 'dash.overview', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { href: '/dashboard/groups', labelKey: 'groups.title', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
  { href: '/dashboard/abilities', labelKey: 'abilities.title', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { href: '/dashboard/skills', labelKey: 'skills.title', icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z' },
  { href: '/dashboard/audit', labelKey: 'audit.title', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
  { href: '/dashboard/alliance', labelKey: 'alliance.title', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [agentId, setAgentIdState] = useState('')
  const [agentName, setAgentName] = useState('')
  const [savedAgents, setSavedAgents] = useState<SavedAgent[]>([])
  const [showAgentSwitcher, setShowAgentSwitcher] = useState(false)
  const { locale, setLocale, t } = useI18n()

  function loadSavedAgents(): SavedAgent[] {
    if (typeof window === 'undefined') return []
    try {
      return JSON.parse(localStorage.getItem('unendingx_saved_agents') || '[]')
    } catch { return [] }
  }

  function saveCurrentAgent() {
    const id = getAgentId()
    const token = getToken()
    if (!id || !token) return
    const agents = loadSavedAgents()
    const existing = agents.findIndex(a => a.id === id)
    if (existing >= 0) {
      agents[existing].token = token
    } else {
      agents.push({ id, name: agentName || id.slice(0, 8), token })
    }
    localStorage.setItem('unendingx_saved_agents', JSON.stringify(agents))
    setSavedAgents(agents)
  }

  function switchToAgent(agent: SavedAgent) {
    setToken(agent.token)
    setAgentId(agent.id)
    setAgentIdState(agent.id)
    setAgentName(agent.name)
    setShowAgentSwitcher(false)
    router.refresh()
  }

  function handleLogout() {
    saveCurrentAgent()
    clearAuth()
    router.push('/login')
  }

  useEffect(() => {
    const id = getAgentId() || ''
    setAgentIdState(id)
    const agents = loadSavedAgents()
    setSavedAgents(agents)
    const found = agents.find(a => a.id === id)
    if (found) setAgentName(found.name)
  }, [])

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col">
        <div className="px-6 py-5 border-b border-slate-100">
          <h1 className="text-xl font-bold text-primary-600">{t('app.title')}</h1>
          <p className="mt-0.5 text-xs text-slate-400">{t('app.subtitle')}</p>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV_KEYS.map(item => {
            const active = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  active
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <svg className="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                </svg>
                {t(item.labelKey)}
              </Link>
            )
          })}
        </nav>

        <div className="px-4 py-4 border-t border-slate-100">
          {/* Language Switcher */}
          <button
            onClick={() => setLocale(locale === 'zh' ? 'en' : 'zh')}
            className="mb-3 w-full flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:border-slate-300"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
            {t('lang.switch')}
          </button>

          <div className="mb-3 rounded-lg bg-slate-50 p-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-400">{t('alliance.current_agent') || '当前智能体'}</p>
              {savedAgents.length > 0 && (
                <button onClick={() => setShowAgentSwitcher(v => !v)}
                  className="text-xs text-indigo-600 hover:underline">
                  {t('alliance.switch') || '切换'}
                </button>
              )}
            </div>
            <p className="text-sm font-medium text-slate-700 truncate" title={agentId}>
              {agentName || (agentId ? `${agentId.slice(0, 8)}…` : '—')}
            </p>
            {showAgentSwitcher && savedAgents.length > 0 && (
              <div className="mt-2 border-t border-slate-200 pt-2 space-y-1">
                {savedAgents.map(a => (
                  <button key={a.id}
                    onClick={() => switchToAgent(a)}
                    className={`w-full text-left text-xs px-2 py-1.5 rounded transition ${
                      a.id === agentId ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-slate-100 text-slate-600'
                    }`}>
                    <span className="font-medium">{a.name}</span>
                    <span className="block text-slate-400 font-mono">{a.id.slice(0, 12)}…</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-red-50 hover:text-red-600 transition"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {t('auth.signout')}
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-6xl p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
