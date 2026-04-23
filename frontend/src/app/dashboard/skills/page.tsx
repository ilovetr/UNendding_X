'use client'

import { useEffect, useState, useCallback } from 'react'
import { api, SkillToken, Ability, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

export default function SkillsPage() {
  const { t } = useI18n()
  const [tokens, setTokens] = useState<SkillToken[]>([])
  const [abilities, setAbilities] = useState<Ability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showInstall, setShowInstall] = useState(false)
  const [form, setForm] = useState({ skill_name: '', version: '1.0.0', ability_ids: [] as string[] })
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [newToken, setNewToken] = useState('')

  const fetchTokens = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [tk, ab] = await Promise.all([api.listMyTokens(), api.listMyAbilities()])
      setTokens(tk)
      setAbilities(ab)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchTokens() }, [fetchTokens])

  async function handleInstall(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setMsg(null)
    try {
      const res = await api.installSkill({
        skill_name: form.skill_name,
        version: form.version,
        ability_ids: form.ability_ids.length > 0 ? form.ability_ids : undefined,
      })
      setNewToken(res.token)
      setMsg({ type: 'ok', text: `${t('skills.token_issued')}: ${new Date(res.expires_at).toLocaleString()}` })
      setShowInstall(false)
      setForm({ skill_name: '', version: '1.0.0', ability_ids: [] })
      fetchTokens()
    } catch (err) {
      setMsg({ type: 'err', text: err instanceof ApiError ? err.message : 'Failed' })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRevoke(tokenId: string) {
    if (!confirm(t('skills.revoke_confirm'))) return
    try {
      await api.revokeToken(tokenId)
      fetchTokens()
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Failed')
    }
  }

  function toggleAbility(id: string) {
    setForm(f => ({
      ...f,
      ability_ids: f.ability_ids.includes(id) ? f.ability_ids.filter(x => x !== id) : [...f.ability_ids, id],
    }))
  }

  function isExpired(expires_at: string) {
    return new Date(expires_at) < new Date()
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900">{t('skills.title')}</h2>
        <button onClick={() => setShowInstall(true)} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700">
          {t('skills.install_skill')}
        </button>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-600">{error}</div>}
      {msg && (
        <div className={`mb-4 rounded-lg border px-4 py-2 text-sm ${msg.type === 'ok' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-600'}`}>
          {msg.text}
        </div>
      )}

      {/* New token display */}
      {newToken && (
        <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="mb-2 text-sm font-medium text-emerald-700">{t('skills.new_token')}</p>
          <div className="break-all rounded bg-white p-3 text-xs font-mono text-slate-600">{newToken}</div>
          <button onClick={() => { navigator.clipboard.writeText(newToken); setMsg({ type: 'ok', text: t('skills.copied') }) }}
            className="mt-2 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white">
            {t('skills.copy')}
          </button>
        </div>
      )}

      {showInstall && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">{t('skills.install_skill')}</h3>
            <form onSubmit={handleInstall} className="space-y-3">
              <input required placeholder={t('skills.skill_name')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={form.skill_name} onChange={e => setForm({...form, skill_name: e.target.value})} />
              <input required placeholder={t('abilities.version') + ' (e.g. 1.0.0)'} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={form.version} onChange={e => setForm({...form, version: e.target.value})} />
              {abilities.length > 0 && (
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">{t('skills.grant_abilities')}</label>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {abilities.map(a => (
                      <label key={a.id} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm cursor-pointer hover:bg-slate-50">
                        <input type="checkbox" className="rounded" checked={form.ability_ids.includes(a.id)} onChange={() => toggleAbility(a.id)} />
                        <span className="font-medium">{a.name}</span>
                        <span className="text-xs text-slate-400">{a.version}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowInstall(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">{t('skills.cancel')}</button>
                <button type="submit" disabled={submitting} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{submitting ? t('skills.installing') : t('skills.install')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="space-y-3">{[1,2].map(i => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-200" />)}</div>
      ) : tokens.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-slate-500">
          {t('skills.no_tokens')}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600">{t('skills.skill_name')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('abilities.version')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('skills.permissions')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('skills.expires')}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tokens.map(tk => (
                <tr key={tk.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{tk.skill_name}</td>
                  <td className="px-4 py-3 font-mono text-slate-500">{tk.version}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {tk.permissions.length > 0 ? `${tk.permissions.length} ${t('skills.abilities_count')}` : t('skills.none')}
                  </td>
                  <td className="px-4 py-3">
                    <span className={isExpired(tk.expires_at) ? 'text-red-500' : 'text-slate-500'}>
                      {new Date(tk.expires_at).toLocaleString()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleRevoke(tk.id)} className="text-xs text-red-500 hover:underline">{t('skills.revoke')}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
