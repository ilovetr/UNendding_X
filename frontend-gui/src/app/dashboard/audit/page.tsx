'use client'

import { useEffect, useState } from 'react'
import { api, AuditLog, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

export default function AuditPage() {
  const { t } = useI18n()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [action, setAction] = useState('')
  const [tab, setTab] = useState<'mine' | 'all'>('mine')

  useEffect(() => {
    setLoading(true)
    setError('')
    api.listAuditLogs({ action: action || undefined, limit: 100, mine: tab === 'mine' })
      .then(setLogs)
      .catch(err => setError(err instanceof ApiError ? err.message : 'Failed'))
      .finally(() => setLoading(false))
  }, [action, tab])

  const actions = ['agent_register', 'agent_login', 'group_create', 'group_join', 'group_leave', 'ability_register', 'skill_install', 'skill_verify']

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900">{t('audit.title')}</h2>
        <select className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" value={action} onChange={e => setAction(e.target.value)}>
          <option value="">{t('audit.all_actions')}</option>
          {actions.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1 w-fit">
        {(['mine', 'all'] as const).map(tabKey => (
          <button key={tabKey} onClick={() => setTab(tabKey)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${tab === tabKey ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            {tabKey === 'mine' ? t('audit.my_logs') : t('audit.all_logs')}
          </button>
        ))}
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-600">{error}</div>}

      {loading ? (
        <div className="space-y-2">{[1,2,3,4,5].map(i => <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-200" />)}</div>
      ) : logs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-slate-500">
          {t('audit.no_logs')}
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map(log => (
            <div key={log.id} className="flex items-start gap-4 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
              <div className="flex-shrink-0">
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                  log.action.includes('register') || log.action.includes('create') ? 'bg-emerald-100 text-emerald-700' :
                  log.action.includes('login') || log.action.includes('join') ? 'bg-blue-100 text-blue-700' :
                  log.action.includes('leave') || log.action.includes('revoke') ? 'bg-amber-100 text-amber-700' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {log.action}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-700">{Object.entries(log.details || {}).map(([k, v]) => `${k}: ${String(v)}`).join(' · ')}</p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {log.agent_id?.slice(0, 8)} · {new Date(log.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
