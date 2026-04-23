'use client'

import { useEffect, useState, useCallback } from 'react'
import { api, Ability, CategoryInfo, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

type Tab = 'mine' | 'all'
type ModalMode = null | 'register' | 'edit' | 'batch'

export default function AbilitiesPage() {
  const { t, locale } = useI18n()
  const [tab, setTab] = useState<Tab>('mine')
  const [abilities, setAbilities] = useState<Ability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState<ModalMode>(null)
  const [editTarget, setEditTarget] = useState<Ability | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState('')

  // Register form
  const [regForm, setRegForm] = useState({ name: '', description: '', version: '1.0.0', definition: '{"input":"text","output":"result"}' })

  // Edit form
  const [editForm, setEditForm] = useState({ description: '', version: '', definition: '' })

  // Batch form
  const [batchJson, setBatchJson] = useState('[\n  {\n    "name": "能力名称",\n    "description": "描述",\n    "version": "1.0.0",\n    "definition": {"input": "text", "output": "result"}\n  }\n]')
  const [batchResult, setBatchResult] = useState<Ability[]>([])

  // Discover form
  const [discoverForm, setDiscoverForm] = useState('[\n  {\n    "name": "web_search",\n    "description": "网络搜索",\n    "version": "1.0.0",\n    "definition": {"type": "tool", "input": {"query": "string"}, "output": "results"}\n  },\n  {\n    "name": "code_interpreter",\n    "description": "代码执行",\n    "version": "1.0.0",\n    "definition": {"type": "tool", "input": {"code": "string"}, "output": "result"}\n  }\n]')
  const [discoverResult, setDiscoverResult] = useState<Ability[]>([])

  const fetchAbilities = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = tab === 'mine' ? await api.listMyAbilities() : await api.listAbilities()
      setAbilities(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => { fetchAbilities() }, [fetchAbilities])

  function openEdit(a: Ability) {
    setEditTarget(a)
    setEditForm({ description: a.description || '', version: a.version, definition: JSON.stringify(a.definition, null, 2) })
    setModal('edit')
    setMsg('')
  }

  function closeModal() {
    setModal(null)
    setEditTarget(null)
    setRegForm({ name: '', description: '', version: '1.0.0', definition: '{"input":"text","output":"result"}' })
    setBatchJson('[\n  {\n    "name": "能力名称",\n    "description": "描述",\n    "version": "1.0.0",\n    "definition": {"input": "text", "output": "result"}\n  }\n]')
    setBatchResult([])
    setDiscoverForm('[\n  {\n    "name": "web_search",\n    "description": "网络搜索",\n    "version": "1.0.0",\n    "definition": {"type": "tool", "input": {"query": "string"}, "output": "results"}\n  },\n  {\n    "name": "code_interpreter",\n    "description": "代码执行",\n    "version": "1.0.0",\n    "definition": {"type": "tool", "input": {"code": "string"}, "output": "result"}\n  }\n]')
    setDiscoverResult([])
    setMsg('')
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setMsg('')
    try {
      const a = await api.registerAbility({
        name: regForm.name,
        description: regForm.description,
        version: regForm.version,
        definition: JSON.parse(regForm.definition),
      })
      setMsg(`${t('abilities.registered_msg')}: ${a.name} v${a.version} (ID: ${a.id.slice(0, 8)})`)
      closeModal()
      if (tab === 'mine') fetchAbilities()
    } catch (err) {
      setMsg(`Error: ${err instanceof ApiError ? err.message : 'Failed'}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEdit(e: React.FormEvent) {
    e.preventDefault()
    if (!editTarget) return
    setSubmitting(true)
    setMsg('')
    try {
      const updateData: Parameters<typeof api.updateAbility>[1] = {}
      if (editForm.description !== (editTarget.description || '')) updateData.description = editForm.description
      if (editForm.definition !== JSON.stringify(editTarget.definition, null, 2)) {
        updateData.definition = JSON.parse(editForm.definition)
      }
      // Version can only increase
      if (compareVersion(editForm.version, editTarget.version) > 0) {
        updateData.version = editForm.version
      } else if (editForm.version !== editTarget.version) {
        setMsg(`⚠️ 版本号只能增加，当前最高: ${editTarget.version}`)
        setSubmitting(false)
        return
      }
      if (Object.keys(updateData).length === 0) {
        setMsg('没有改动')
        setSubmitting(false)
        return
      }
      const updated = await api.updateAbility(editTarget.id, updateData)
      setMsg(`✅ 已更新: ${updated.name} → v${updated.version}`)
      closeModal()
      fetchAbilities()
    } catch (err) {
      setMsg(`Error: ${err instanceof ApiError ? err.message : 'Failed'}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleBatch(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setMsg('')
    setBatchResult([])
    try {
      const items = JSON.parse(batchJson)
      const result = await api.batchRegisterAbilities(items)
      setBatchResult(result)
      setMsg(`✅ 批量注册完成: ${result.length} 个能力`)
      if (tab === 'mine') fetchAbilities()
    } catch (err) {
      setMsg(`Error: ${err instanceof ApiError ? err.message : 'JSON 格式错误或请求失败'}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDiscover(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setMsg('')
    setDiscoverResult([])
    try {
      const items = JSON.parse(discoverForm)
      const result = await api.batchRegisterAbilities(items)
      setDiscoverResult(result)
      setMsg(`✅ 自动发现注册完成: ${result.length} 个能力`)
      if (tab === 'mine') fetchAbilities()
    } catch (err) {
      setMsg(`Error: ${err instanceof ApiError ? err.message : 'JSON 格式错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900">{t('abilities.title')}</h2>
        <div className="flex gap-2">
          <button onClick={() => { closeModal(); setModal('batch') }}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50">
            {t('abilities.batch_register') || '批量注册'}
          </button>
          <button onClick={() => { closeModal(); setModal('register') }}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-primary-700">
            {t('abilities.register_ability')}
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1 w-fit">
          {([['mine', 'groups.my_groups'], ['public', 'groups.public_groups']] as [Tab, string][]).map(([tKey, labelKey]) => (
            <button key={tKey} onClick={() => setTab(tKey)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${tab === tKey ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
              {t(labelKey)}
            </button>
          ))}
        </div>
        {tab === 'mine' && (
          <button onClick={() => { closeModal(); setModal('batch') }}
            className="ml-2 flex items-center gap-1 rounded-lg border border-purple-300 bg-purple-50 px-3 py-1.5 text-sm font-medium text-purple-700 transition hover:bg-purple-100">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {t('abilities.auto_discover') || '自动发现注册'}
          </button>
        )}
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-600">{error}</div>}
      {msg && <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-2 text-sm text-green-700">{msg}</div>}

      {/* Register Modal */}
      {modal === 'register' && (
        <Modal title={t('abilities.register_ability')} onClose={closeModal}>
          <form onSubmit={handleRegister} className="space-y-3">
            <input required placeholder={t('abilities.ability_name')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={regForm.name} onChange={e => setRegForm({...regForm, name: e.target.value})} />
            <input required placeholder={t('abilities.version') + ' (e.g. 1.0.0)'} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={regForm.version} onChange={e => setRegForm({...regForm, version: e.target.value})} />
            <textarea placeholder={t('groups.description')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" rows={2} value={regForm.description} onChange={e => setRegForm({...regForm, description: e.target.value})} />
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Definition (JSON)</label>
              <textarea required placeholder='{"input":"text","output":"summary"}' className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono" rows={3} value={regForm.definition} onChange={e => setRegForm({...regForm, definition: e.target.value})} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={closeModal} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">{t('abilities.cancel')}</button>
              <button type="submit" disabled={submitting} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{submitting ? t('abilities.registering') : t('abilities.register')}</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Edit Modal */}
      {modal === 'edit' && editTarget && (
        <Modal title={`${t('abilities.edit_ability') || '编辑能力'}: ${editTarget.name}`} onClose={closeModal}>
          <form onSubmit={handleEdit} className="space-y-3">
            <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 text-sm text-slate-500">
              ID: <span className="font-mono">{editTarget.id}</span>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">{t('abilities.version')}（只能增大，当前: {editTarget.version}）</label>
              <input placeholder="如 1.1.0，留空不修改" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono" value={editForm.version} onChange={e => setEditForm({...editForm, version: e.target.value})} />
            </div>
            <textarea placeholder={t('groups.description')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" rows={2} value={editForm.description} onChange={e => setEditForm({...editForm, description: e.target.value})} />
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Definition（JSON）</label>
              <textarea className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono" rows={4} value={editForm.definition} onChange={e => setEditForm({...editForm, definition: e.target.value})} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={closeModal} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">{t('abilities.cancel')}</button>
              <button type="submit" disabled={submitting} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{submitting ? '保存中...' : t('abilities.save') || '保存'}</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Batch Register / Auto-Discover Modal */}
      {modal === 'batch' && (
        <Modal title={`${t('abilities.batch_register') || '批量注册'} / ${t('abilities.auto_discover') || '自动发现'}`} onClose={closeModal}>
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              输入能力列表 JSON，自动调用 <span className="font-mono text-xs bg-slate-100 px-1 rounded">POST /api/abilities/batch</span> 批量注册。同名能力仅当版本号更高时更新。
            </p>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">能力列表（JSON 数组）</label>
              <textarea
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono"
                rows={10}
                value={batchJson}
                onChange={e => setBatchJson(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={closeModal} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">{t('abilities.cancel')}</button>
              <button onClick={handleBatch as any} disabled={submitting}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                {submitting ? '处理中...' : '批量注册'}
              </button>
            </div>

            {batchResult.length > 0 && (
              <div className="mt-3 rounded-lg border border-green-200 bg-green-50 p-3">
                <p className="text-sm font-medium text-green-700 mb-2">注册结果：</p>
                <div className="space-y-1">
                  {batchResult.map(a => (
                    <div key={a.id} className="text-xs text-green-700 font-mono">
                      ✓ {a.name} v{a.version} ({a.id.slice(0, 8)})
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="border-t border-slate-200 pt-3 mt-3">
              <p className="text-sm font-medium text-purple-700 mb-2">{t('abilities.auto_discover') || '自动发现注册'}</p>
              <p className="text-xs text-slate-500 mb-2">填写希望注册的能力列表（示例：智能体通常具备的能力类型），一键批量注册到川流。</p>
              <textarea
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono"
                rows={8}
                value={discoverForm}
                onChange={e => setDiscoverForm(e.target.value)}
              />
              <div className="flex justify-end gap-2 mt-2">
                <button onClick={handleDiscover as any} disabled={submitting}
                  className="flex items-center gap-1 rounded-lg border border-purple-300 bg-purple-50 px-4 py-2 text-sm font-medium text-purple-700 disabled:opacity-50">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  {submitting ? '注册中...' : '自动发现注册'}
                </button>
              </div>
              {discoverResult.length > 0 && (
                <div className="mt-2 rounded-lg border border-purple-200 bg-purple-50 p-3">
                  <p className="text-sm font-medium text-purple-700 mb-1">已注册：</p>
                  {discoverResult.map(a => (
                    <div key={a.id} className="text-xs text-purple-700 font-mono">✓ {a.name} v{a.version}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* Table */}
      {loading ? (
        <div className="space-y-3">{[1,2].map(i => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-200" />)}</div>
      ) : abilities.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-slate-500">
          {t('abilities.no_abilities')}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-600">{t('abilities.ability_name')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('abilities.version')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('abilities.status')}</th>
                <th className="px-4 py-3 font-medium text-slate-600">{t('groups.description')}</th>
                {tab === 'mine' && <th className="px-4 py-3"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {abilities.map(a => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{a.name}</div>
                    <div className="text-xs text-slate-400 font-mono">{a.id.slice(0, 16)}…</div>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-500">{a.version}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${a.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500 max-w-xs truncate">{a.description || '—'}</td>
                  {tab === 'mine' && (
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => openEdit(a)} className="text-xs text-indigo-600 hover:underline mr-3">{t('abilities.edit_ability') || '编辑'}</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Shared Modal component ──────────────────────────────────────────────────
function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl max-h-[85vh] overflow-y-auto">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ── Version comparison ──────────────────────────────────────────────────────
function compareVersion(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < 3; i++) {
    const va = pa[i] || 0, vb = pb[i] || 0
    if (va > vb) return 1
    if (va < vb) return -1
  }
  return 0
}
