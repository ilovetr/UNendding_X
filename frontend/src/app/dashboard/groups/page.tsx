'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { api, Group, CategoryInfo, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

type Tab = 'mine' | 'public'

export default function GroupsPage() {
  const { t, locale } = useI18n()
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('mine')
  const [groups, setGroups] = useState<Group[]>([])
  const [categories, setCategories] = useState<CategoryInfo[]>([])
  const [filterCategory, setFilterCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [showJoin, setShowJoin] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', description: '', privacy: 'public' as 'public' | 'private', category: 'other', password: '' })
  const [joinCode, setJoinCode] = useState('')
  const [joinPassword, setJoinPassword] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState('')
  const [generatingDesc, setGeneratingDesc] = useState(false)

  const catLabel = (c: CategoryInfo) => locale === 'zh' ? c.label_zh : c.label_en
  const groupLabel = (g: Group) => locale === 'zh' ? g.category_label_zh : g.category_label_en

  const fetchCategories = useCallback(async () => {
    try {
      const data = await api.listCategories()
      setCategories(data)
    } catch { /* silent */
    }
  }, [])

  const fetchGroups = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = tab === 'mine'
        ? await api.listMyGroups()
        : await api.listGroups({ category: filterCategory || undefined })
      setGroups(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [tab, filterCategory])

  useEffect(() => { fetchGroups() }, [fetchGroups])
  useEffect(() => { fetchCategories() }, [fetchCategories])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setActionLoading(true)
    setActionMsg('')
    try {
      const g = await api.createGroup({
        name: createForm.name,
        description: createForm.description,
        privacy: createForm.privacy,
        category: createForm.category,
        password: createForm.privacy === 'private' ? createForm.password : undefined,
      })
      setActionMsg(`${t('groups.created_msg')}: ${g.name}. ${t('groups.invite_code_label')}: ${g.invite_code}`)
      setShowCreate(false)
      setCreateForm({ name: '', description: '', privacy: 'public', category: 'other', password: '' })
      if (tab === 'mine') fetchGroups()
    } catch (err) {
      setActionMsg(`Error: ${err instanceof ApiError ? err.message : 'Failed'}`)
    } finally {
      setActionLoading(false)
    }
  }

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault()
    setActionLoading(true)
    setActionMsg('')
    try {
      const g = await api.joinGroup({ invite_code: joinCode, password: joinPassword || undefined })
      setActionMsg(`${t('groups.joined_msg')}: ${g.name}`)
      setShowJoin(false)
      setJoinCode('')
      setJoinPassword('')
      if (tab === 'mine') fetchGroups()
    } catch (err) {
      setActionMsg(`Error: ${err instanceof ApiError ? err.message : 'Failed'}`)
    } finally {
      setActionLoading(false)
    }
  }

  async function handleLeave(groupId: string) {
    if (!confirm(t('groups.leave_confirm'))) return
    try {
      await api.leaveGroup(groupId)
      fetchGroups()
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Failed')
    }
  }

  async function handleGenerateDescription() {
    if (!createForm.name.trim()) {
      setActionMsg(t('groups.name_required') || '请先输入群组名称')
      return
    }
    setGeneratingDesc(true)
    setActionMsg('')
    try {
      const result = await api.generateDescription({
        name: createForm.name,
        category: createForm.category,
      })
      setCreateForm({...createForm, description: result.description})
      setActionMsg('')
    } catch (err) {
      setActionMsg(`AI: ${err instanceof ApiError ? err.message : 'Failed'}`)
    } finally {
      setGeneratingDesc(false)
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900">{t('groups.title')}</h2>
        <div className="flex gap-2">
          <button onClick={() => setShowJoin(true)} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50">
            {t('groups.join_group')}
          </button>
          <button onClick={() => setShowCreate(true)} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700">
            {t('groups.create_group')}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex items-center gap-1 rounded-lg bg-slate-100 p-1 w-fit">
        {([['mine', 'groups.my_groups'], ['public', 'groups.public_groups']] as [Tab, string][]).map(([tKey, labelKey]) => (
          <button key={tKey} onClick={() => setTab(tKey)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${tab === tKey ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            {t(labelKey)}
          </button>
        ))}
      </div>

      {/* Category filter (public tab only) */}
      {tab === 'public' && (
        <div className="mb-4 flex items-center gap-2">
          <label className="text-sm text-slate-600">{t('groups.category') || '分类'}:</label>
          <select
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
          >
            <option value="">{t('groups.all_categories') || '全部'}</option>
            {categories.map(c => (
              <option key={c.value} value={c.value}>{catLabel(c)}</option>
            ))}
          </select>
        </div>
      )}

      {error && <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-600">{error}</div>}
      {actionMsg && <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-2 text-sm text-green-700">{actionMsg}</div>}

      {/* Modals */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">{t('groups.create_group')}</h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required placeholder={t('groups.group_name')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={createForm.name} onChange={e => setCreateForm({...createForm, name: e.target.value})} />
              <div className="relative">
                <textarea placeholder={t('groups.description_optional')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm pr-20" rows={2} value={createForm.description} onChange={e => setCreateForm({...createForm, description: e.target.value})} />
                <button
                  type="button"
                  disabled={generatingDesc || !createForm.name.trim()}
                  onClick={handleGenerateDescription}
                  className="absolute right-2 top-2 flex items-center gap-1 rounded-md bg-purple-100 px-2 py-1 text-xs font-medium text-purple-700 transition hover:bg-purple-200 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {generatingDesc ? (
                    <span className="inline-block h-3 w-3 animate-spin rounded-full border border-purple-300 border-t-purple-600" />
                  ) : (
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  )}
                  {t('groups.ai_generate') || 'AI生成'}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">{t('groups.privacy')}</label>
                  <select className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={createForm.privacy} onChange={e => setCreateForm({...createForm, privacy: e.target.value as 'public' | 'private'})}>
                    <option value="public">{t('groups.public_visible')}</option>
                    <option value="private">{t('groups.private_invite')}</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">{t('groups.category') || '分类'}</label>
                  <select className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={createForm.category} onChange={e => setCreateForm({...createForm, category: e.target.value})}>
                    {categories.map(c => (
                      <option key={c.value} value={c.value}>{catLabel(c)}</option>
                    ))}
                  </select>
                </div>
              </div>
              {createForm.privacy === 'private' && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">{t('groups.password') || '加入密码'}</label>
                  <input
                    required
                    type="password"
                    placeholder={t('groups.password_placeholder') || '最少4位'}
                    minLength={4}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    value={createForm.password}
                    onChange={e => setCreateForm({...createForm, password: e.target.value})}
                  />
                </div>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">{t('groups.cancel')}</button>
                <button type="submit" disabled={actionLoading} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{actionLoading ? t('groups.creating') : t('groups.create')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showJoin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">{t('groups.join_group')}</h3>
            <form onSubmit={handleJoin} className="space-y-3">
              <input required placeholder={t('groups.invite_code')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono" value={joinCode} onChange={e => setJoinCode(e.target.value)} />
              <input
                type="password"
                placeholder={t('groups.password_placeholder') || '加入密码（私密群组必填）'}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={joinPassword}
                onChange={e => setJoinPassword(e.target.value)}
              />
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowJoin(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">{t('groups.cancel')}</button>
                <button type="submit" disabled={actionLoading} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{actionLoading ? t('groups.joining') : t('groups.join')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-200" />)}</div>
      ) : groups.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-slate-500">
          {t('groups.no_groups')}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600">{t('groups.group_name')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('groups.description')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('groups.category') || '分类'}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('groups.members')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('groups.privacy')}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {groups.map(g => (
                <tr key={g.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{g.name}</td>
                  <td className="px-4 py-3 text-slate-500 max-w-xs truncate">{g.description || '—'}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                      {groupLabel(g)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{g.member_count}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${g.privacy === 'public' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
                      {g.privacy === 'private' && (
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                      )}
                      {g.privacy === 'public' ? t('groups.public_visible').split('(')[0].trim() : t('groups.private_invite').split('(')[0].trim()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {tab === 'mine' && (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => router.push(`/dashboard/groups/${g.id}/chat`)}
                          className="inline-flex items-center gap-1 rounded-lg bg-indigo-100 px-3 py-1.5 text-xs font-medium text-indigo-700 transition hover:bg-indigo-200"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                          </svg>
                          {t('chat.enter') || '进入聊天'}
                        </button>
                        <button onClick={() => handleLeave(g.id)} className="text-xs text-red-500 hover:underline">{t('groups.leave')}</button>
                      </div>
                    )}
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
