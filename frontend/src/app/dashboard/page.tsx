'use client'

import { useEffect, useState } from 'react'
import { api, getAgentId, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

interface Stats {
  groups: number
  abilities: number
  tokens: number
}

export default function DashboardPage() {
  const { t } = useI18n()
  const [stats, setStats] = useState<Stats>({ groups: 0, abilities: 0, tokens: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.listMyGroups(),
      api.listMyAbilities(),
      api.listMyTokens(),
    ])
      .then(([groups, abilities, tokens]) => {
        setStats({
          groups: groups.length,
          abilities: abilities.length,
          tokens: tokens.length,
        })
      })
      .catch(err => setError(err instanceof ApiError ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const cards = [
    { label: t('dash.my_groups'), value: stats.groups, href: '/dashboard/groups', color: 'bg-indigo-50 text-indigo-600', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
    { label: t('dash.my_abilities'), value: stats.abilities, href: '/dashboard/abilities', color: 'bg-cyan-50 text-cyan-600', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
    { label: t('dash.skill_tokens'), value: stats.tokens, href: '/dashboard/skills', color: 'bg-emerald-50 text-emerald-600', icon: 'M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z' },
  ]

  const steps = [
    { title: t('dash.step1_title'), desc: t('dash.step1_desc') },
    { title: t('dash.step2_title'), desc: t('dash.step2_desc') },
    { title: t('dash.step3_title'), desc: t('dash.step3_desc') },
  ]

  return (
    <div>
      <h2 className="mb-6 text-2xl font-bold text-slate-900">{t('dash.overview')}</h2>

      {error && (
        <div className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        {cards.map(card => (
          <a
            key={card.label}
            href={card.href}
            className="block rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md hover:border-slate-300"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">{card.label}</p>
                {loading ? (
                  <div className="mt-1 h-9 w-12 animate-pulse rounded bg-slate-100" />
                ) : (
                  <p className="mt-1 text-4xl font-bold text-slate-900">{card.value}</p>
                )}
              </div>
              <div className={`rounded-xl p-3 ${card.color}`}>
                <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={card.icon} />
                </svg>
              </div>
            </div>
          </a>
        ))}
      </div>

      <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-slate-900">{t('dash.quick_start')}</h3>
        <div className="space-y-3 text-sm">
          {steps.map((step, i) => (
            <div key={i} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700">{i + 1}</span>
              <div>
                <p className="font-medium text-slate-800">{step.title}</p>
                <p className="text-slate-500">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
