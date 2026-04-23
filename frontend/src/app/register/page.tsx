'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api, setToken, setAgentId, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

export default function RegisterPage() {
  const router = useRouter()
  const { locale, setLocale, t } = useI18n()
  const [form, setForm] = useState({ name: '', did: '', endpoint: '' })
  const [result, setResult] = useState<{ id: string; api_key: string } | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [autoLogin, setAutoLogin] = useState(true)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const data = { name: form.name, ...(form.did ? { did: form.did } : {}), ...(form.endpoint ? { endpoint: form.endpoint } : {}) }

      const agent = await api.register(data)

      if (autoLogin) {
        const res = await api.login({ id: agent.id, api_key: agent.api_key! })
        setToken(res.access_token)
        setAgentId(agent.id)
        router.push('/dashboard')
      } else {
        setResult({ id: agent.id, api_key: agent.api_key! })
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-primary-600">{t('app.title')}</h1>
          <p className="mt-2 text-slate-500">{t('auth.register_your_agent')}</p>
          <button
            onClick={() => setLocale(locale === 'zh' ? 'en' : 'zh')}
            className="mt-2 text-xs text-slate-400 hover:text-slate-600 transition"
          >
            {t('lang.switch')}
          </button>
        </div>

        {result ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="mb-4 flex items-center gap-2 text-green-600">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="font-semibold">{t('auth.registration_success')}</span>
            </div>
            <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 p-4">
              <p className="mb-2 text-sm font-medium text-amber-700">{t('auth.save_credentials')}</p>
            </div>
            <div className="mb-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500 uppercase">{t('auth.agent_id')}</label>
                <div className="break-all rounded-lg bg-slate-100 px-3 py-2 text-sm font-mono text-slate-800">{result.id}</div>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-500 uppercase">{t('auth.api_key')}</label>
                <div className="break-all rounded-lg bg-slate-100 px-3 py-2 text-sm font-mono text-slate-800">{result.api_key}</div>
              </div>
            </div>
            <Link href="/login" className="block w-full rounded-lg bg-primary-600 py-2.5 text-center text-sm font-medium text-white transition hover:bg-primary-700">
              {t('auth.go_to_login')}
            </Link>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="mb-6 text-xl font-semibold text-slate-800">{t('auth.register')}</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  {t('auth.agent_name')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="My AI Agent"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">{t('auth.did_url')} <span className="text-slate-400">{t('auth.did_optional')}</span></label>
                <input
                  type="text"
                  placeholder="did:example:xxxxxxxx"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                  value={form.did}
                  onChange={e => setForm({ ...form, did: e.target.value })}
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">{t('auth.endpoint_url')} <span className="text-slate-400">{t('auth.endpoint_optional')}</span></label>
                <input
                  type="url"
                  placeholder="http://localhost:9000"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                  value={form.endpoint}
                  onChange={e => setForm({ ...form, endpoint: e.target.value })}
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={autoLogin}
                  onChange={e => setAutoLogin(e.target.checked)}
                  className="rounded border-slate-300"
                />
                {t('auth.auto_login')}
              </label>

              {error && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-600">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-primary-600 py-2.5 text-sm font-medium text-white transition hover:bg-primary-700 disabled:opacity-50"
              >
                {loading ? t('auth.registering') : t('auth.register')}
              </button>
            </form>

            <div className="mt-4 text-center text-sm text-slate-500">
              {t('auth.already_registered')}{' '}
              <Link href="/login" className="text-primary-600 hover:underline">
                {t('auth.signin')}
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
