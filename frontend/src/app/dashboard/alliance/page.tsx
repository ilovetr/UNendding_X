'use client'

import { useEffect, useState, useCallback } from 'react'
import { api, AllianceMember, AllianceGroup, AllianceAbility, AllianceSkillToken, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

type SubTab = 'groups' | 'abilities' | 'skills'

export default function AlliancePage() {
  const { t } = useI18n()
  const [members, setMembers] = useState<AllianceMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ agent_id: '', label: '' })
  const [submitting, setSubmitting] = useState(false)

  // Detail view
  const [selectedMember, setSelectedMember] = useState<AllianceMember | null>(null)
  const [detailTab, setDetailTab] = useState<SubTab>('groups')
  const [detailData, setDetailData] = useState<AllianceGroup[] | AllianceAbility[] | AllianceSkillToken[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const fetchMembers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listAllianceMembers()
      setMembers(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchMembers() }, [fetchMembers])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!addForm.agent_id.trim()) return
    setSubmitting(true)
    setMsg('')
    try {
      const m = await api.addAllianceMember(addForm.agent_id.trim(), addForm.label || undefined)
      setMembers(prev => [...prev.filter(x => x.alliance_id !== m.alliance_id), m])
      setMsg(`✅ 已添加: ${m.agent.name}`)
      setShowAdd(false)
      setAddForm({ agent_id: '', label: '' })
    } catch (err) {
      setMsg(`Error: ${err instanceof ApiError ? err.message : 'Failed'}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRemove(member: AllianceMember) {
    if (!confirm(`确定移除与 "${member.agent.name}" 的联盟关系？`)) return
    try {
      await api.removeAllianceMember(member.alliance_id)
      setMembers(prev => prev.filter(m => m.alliance_id !== member.alliance_id))
      if (selectedMember?.alliance_id === member.alliance_id) setSelectedMember(null)
      setMsg(`已移除: ${member.agent.name}`)
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Failed')
    }
  }

  async function viewMember(member: AllianceMember) {
    setSelectedMember(member)
    setDetailTab('groups')
    setDetailData([])
  }

  useEffect(() => {
    if (!selectedMember) return
    setDetailLoading(true)
    const fetchers: Record<SubTab, () => Promise<any>> = {
      groups: () => api.getAllianceGroups(selectedMember.alliance_id),
      abilities: () => api.getAllianceAbilities(selectedMember.alliance_id),
      skills: () => api.getAllianceSkills(selectedMember.alliance_id),
    }
    fetchers[detailTab]()
      .then(setDetailData)
      .catch((err: any) => alert(err instanceof ApiError ? err.message : 'Failed'))
      .finally(() => setDetailLoading(false))
  }, [selectedMember, detailTab])

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900">{t('alliance.title') || '智能体联盟'}</h2>
        <button onClick={() => { setShowAdd(true); setMsg('') }}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700">
          {t('alliance.add_member') || '添加联盟成员'}
        </button>
      </div>

      <p className="mb-4 text-sm text-slate-600">
        {t('alliance.desc') || '将同一人类用户下的多个智能体加入联盟，实现统一管理。共享群组、能力、SKILL令牌和审计日志。'}
      </p>

      {error && <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-600">{error}</div>}
      {msg && <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-2 text-sm text-green-700">{msg}</div>}

      {/* Add modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">{t('alliance.add_member')}</h3>
            <form onSubmit={handleAdd} className="space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  {t('alliance.agent_id') || '智能体 ID'}
                </label>
                <input required placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono"
                  value={addForm.agent_id}
                  onChange={e => setAddForm({ ...addForm, agent_id: e.target.value })} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  {t('alliance.label') || '备注（可选）'}
                </label>
                <input placeholder="e.g. 我的 Claude / 备用智能体"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  value={addForm.label}
                  onChange={e => setAddForm({ ...addForm, label: e.target.value })} />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowAdd(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm">{t('alliance.cancel') || '取消'}</button>
                <button type="submit" disabled={submitting}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                  {submitting ? (t('alliance.adding') || '添加中...') : (t('alliance.add') || '添加')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Members list */}
      {loading ? (
        <div className="space-y-3">{[1,2].map(i => <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-200" />)}</div>
      ) : members.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-slate-500">
          {t('alliance.no_members') || '暂无联盟成员，点击上方按钮添加'}
        </div>
      ) : (
        <div className="space-y-3">
          {members.map(member => (
            <div key={member.alliance_id}
              className={`rounded-xl border p-4 transition cursor-pointer hover:shadow-md ${
                selectedMember?.alliance_id === member.alliance_id
                  ? 'border-indigo-300 bg-indigo-50'
                  : 'border-slate-200 bg-white'
              }`}
              onClick={() => viewMember(member)}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-slate-900">
                      {member.label || member.agent.name}
                    </h3>
                    {member.label && (
                      <span className="text-xs text-slate-400">({member.agent.name})</span>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-xs text-slate-500">
                    <span className="font-mono">{member.agent.id.slice(0, 16)}…</span>
                    <span className="flex items-center gap-1">
                      <span className="h-2 w-2 rounded-full bg-green-500"></span>
                      {member.agent.status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  <span title={t('alliance.groups') || '群组'}>
                    📁 {member.group_count}
                  </span>
                  <span title={t('alliance.abilities') || '能力'}>
                    ⚡ {member.ability_count}
                  </span>
                  <span title={t('alliance.skills') || 'SKILL令牌'}>
                    🔑 {member.skill_token_count}
                  </span>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRemove(member) }}
                    className="ml-2 text-xs text-red-500 hover:underline">
                    {t('alliance.remove') || '移除'}
                  </button>
                </div>
              </div>

              {/* Detail panel */}
              {selectedMember?.alliance_id === member.alliance_id && (
                <div className="mt-4 border-t border-indigo-200 pt-4" onClick={e => e.stopPropagation()}>
                  <div className="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1 w-fit">
                    {(['groups', 'abilities', 'skills'] as SubTab[]).map(tab => (
                      <button key={tab} onClick={() => setDetailTab(tab)}
                        className={`rounded-md px-3 py-1 text-sm font-medium transition ${
                          detailTab === tab ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                        }`}>
                        {tab === 'groups' ? `📁 ${t('alliance.groups')}` :
                         tab === 'abilities' ? `⚡ ${t('alliance.abilities')}` :
                         `🔑 ${t('alliance.skills')}`}
                      </button>
                    ))}
                  </div>

                  {detailLoading ? (
                    <div className="h-20 animate-pulse rounded-lg bg-slate-100" />
                  ) : detailData.length === 0 ? (
                    <div className="py-4 text-center text-sm text-slate-400">
                      {t('alliance.no_data') || '暂无数据'}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {detailTab === 'groups' && (detailData as AllianceGroup[]).map(g => (
                        <div key={g.id} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2">
                          <div>
                            <div className="font-medium text-slate-900">{g.name}</div>
                            <div className="text-xs text-slate-500">{g.description || '—'}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-400">{g.member_count} 人</span>
                            {g.invite_code && (
                              <span className="font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">{g.invite_code}</span>
                            )}
                          </div>
                        </div>
                      ))}
                      {detailTab === 'abilities' && (detailData as AllianceAbility[]).map(a => (
                        <div key={a.id} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2">
                          <div>
                            <div className="font-medium text-slate-900">{a.name}</div>
                            <div className="text-xs text-slate-500">{a.description || '—'}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs text-slate-500">v{a.version}</span>
                            <span className={`rounded-full px-2 py-0.5 text-xs ${
                              a.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                            }`}>{a.status}</span>
                          </div>
                        </div>
                      ))}
                      {detailTab === 'skills' && (detailData as AllianceSkillToken[]).map(s => (
                        <div key={s.id} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-3 py-2">
                          <div>
                            <div className="font-medium text-slate-900">{s.skill_name}</div>
                            <div className="text-xs text-slate-500">{s.permissions.join(', ')}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-400">到期: {new Date(s.expires_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
