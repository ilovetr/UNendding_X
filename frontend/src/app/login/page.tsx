'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api, setToken, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

export default function LoginPage() {
  const router = useRouter()
  const { locale, setLocale, t } = useI18n()
  const [form, setForm] = useState({ id: '', api_key: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.login(form)
      setToken(res.access_token)
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-primary-600">{t('app.title')}</h1>
          <p className="mt-2 text-slate-500">{t('app.subtitle')}</p>
          <button
            onClick={() => setLocale(locale === 'zh' ? 'en' : 'zh')}
            className="mt-2 text-xs text-slate-400 hover:text-slate-600 transition"
          >
            {t('lang.switch')}
          </button>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h2 className="mb-6 text-xl font-semibold text-slate-800">{t('auth.signin')}</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                {t('auth.agent_id')}
              </label>
              <input
                type="text"
                required
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                value={form.id}
                onChange={e => setForm({ ...form, id: e.target.value })}
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                {t('auth.api_key')}
              </label>
              <input
                type="password"
                required
                placeholder="ah_xxxxxxxx..."
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-100"
                value={form.api_key}
                onChange={e => setForm({ ...form, api_key: e.target.value })}
              />
            </div>

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
              {loading ? t('auth.signing_in') : t('auth.signin')}
            </button>
          </form>

          <div className="mt-4 text-center text-sm text-slate-500">
            {t('auth.new_here')}{' '}
            <Link href="/register" className="text-primary-600 hover:underline">
              {t('auth.register')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
