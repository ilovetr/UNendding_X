/**
 * 川流/UnendingX API client.
 * All API calls go through here. Handles auth token injection and error mapping.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: Record<string, unknown>,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface Agent {
  id: string
  name: string
  api_key?: string
  created_at: string
}

export interface Group {
  id: string
  name: string
  description: string
  privacy: 'public' | 'private'
  category: string
  category_label_zh: string
  category_label_en: string
  invite_code?: string
  member_count: number
  has_password: boolean
}

export interface CategoryInfo {
  value: string
  label_zh: string
  label_en: string
}

export interface Ability {
  id: string
  name: string
  description: string
  version: string
  definition: Record<string, unknown>
  status: string
  agent_id: string
}

export interface SkillToken {
  id: string
  skill_name: string
  version: string
  permissions: string[]
  expires_at: string
  issued_at: string
}

export interface AuditLog {
  id: string
  timestamp: string
  action: string
  agent_id?: string
  resource_type?: string
  details: Record<string, unknown>
}

export interface AllianceAgent {
  id: string
  name: string
  endpoint?: string
  status: string
}

export interface AllianceMember {
  alliance_id: string
  agent: AllianceAgent
  label?: string
  status: string
  created_at: string
  group_count: number
  ability_count: number
  skill_token_count: number
}

export interface AllianceGroup {
  id: string
  name: string
  description?: string
  privacy: string
  category: string
  category_label_zh: string
  category_label_en: string
  member_count: number
  invite_code?: string
}

export interface AllianceAbility {
  id: string
  name: string
  description?: string
  version: string
  status: string
  definition: Record<string, unknown>
}

export interface AllianceSkillToken {
  id: string
  skill_name: string
  permissions: string[]
  expires_at: string
  created_at: string
  status: string
}

// ── helpers ──────────────────────────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('unendingx_token')
}

export function setToken(t: string): void {
  localStorage.setItem('unendingx_token', t)
}

export function setAgentId(id: string): void {
  localStorage.setItem('unendingx_agent_id', id)
}

export function getAgentId(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('unendingx_agent_id')
}

export function clearAuth(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem('unendingx_token')
  localStorage.removeItem('unendingx_agent_id')
}

export function getAgentName(): string | null {
  if (typeof window === 'undefined') return null
  const agentId = getAgentId()
  if (!agentId) return null

  try {
    const agents = JSON.parse(localStorage.getItem('unendingx_saved_agents') || '[]')
    const found = agents.find((a: { id: string; name: string }) => a.id === agentId)
    return found?.name || null
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

function errorMessage(body: Record<string, unknown> | null): string {
  if (body?.detail) return String(body.detail)
  if (body?.message) return String(body.message)
  return 'An unexpected error occurred'
}

async function request<T>(
  path: string,
  opts: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers,
  })

  if (!res.ok) {
    let body: Record<string, unknown> = {}
    try { body = await res.json() } catch { /* ignore */ }
    throw new ApiError(res.status, body, errorMessage(body))
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ── API surface ──────────────────────────────────────────────────────────────

export const api = {
  // Auth
  register: (data: { name: string; did?: string; endpoint?: string }) =>
    request<Agent>('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }),

  login: (data: { id: string; api_key: string }) =>
    request<{ access_token: string; expires_in: number }>(
      '/api/auth/token',
      { method: 'POST', body: JSON.stringify(data) },
    ),

  // Groups
  listGroups: (params?: { category?: string }) => {
    const qs = params?.category ? `?category=${params.category}` : ''
    return request<Group[]>(`/api/groups${qs}`)
  },
  listMyGroups: () => request<Group[]>('/api/groups/mine'),
  createGroup: (data: { name: string; description: string; privacy: 'public' | 'private'; category: string; password?: string }) =>
    request<Group>('/api/groups', { method: 'POST', body: JSON.stringify(data) }),
  getGroup: (id: string) => request<Group>(`/api/groups/${id}`),
  joinGroup: (data: { invite_code: string; password?: string }) =>
    request<Group>('/api/groups/join', { method: 'POST', body: JSON.stringify(data) }),
  leaveGroup: (id: string) =>
    request<void>(`/api/groups/${id}/leave`, { method: 'POST' }),
  listCategories: () => request<CategoryInfo[]>('/api/groups/categories'),

  // Abilities
  listAbilities: (params?: { group_id?: string }) => {
    const qs = params?.group_id ? `?group_id=${params.group_id}` : ''
    return request<Ability[]>(`/api/abilities${qs}`)
  },
  listMyAbilities: () => request<Ability[]>('/api/abilities/mine'),
  registerAbility: (data: {
    name: string
    description: string
    version: string
    definition: Record<string, unknown>
    group_id?: string
  }) => request<Ability>('/api/abilities', { method: 'POST', body: JSON.stringify(data) }),
  updateAbility: (id: string, data: {
    description?: string
    version?: string
    definition?: Record<string, unknown>
    status?: string
  }) => request<Ability>(`/api/abilities/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  batchRegisterAbilities: (abilities: Array<{
    name: string
    description?: string
    version: string
    definition: Record<string, unknown>
    group_id?: string
  }>) => request<Ability[]>('/api/abilities/batch', { method: 'POST', body: JSON.stringify({ abilities }) }),

  // Skills
  installSkill: (data: {
    skill_name: string
    version: string
    ability_ids?: string[]
    group_id?: string
  }) => request<{ token: string; skill_name: string; token_id: string; permissions: string[]; expires_at: string }>(
    '/api/skills/install', { method: 'POST', body: JSON.stringify(data) },
  ),
  verifySkill: (token: string) =>
    request<{ valid: boolean; skill_name?: string; revoked?: boolean }>(
      '/api/skills/verify', { method: 'POST', body: JSON.stringify({ token }) },
    ),
  checkSkill: (token: string, ability_id: string) =>
    request<{ allowed: boolean; reason?: string }>(
      '/api/skills/check', { method: 'POST', body: JSON.stringify({ token, ability_id }) },
    ),
  listMyTokens: () => request<SkillToken[]>('/api/skills/my-tokens'),
  revokeToken: (tokenId: string) =>
    request<void>(`/api/skills/${tokenId}`, { method: 'DELETE' }),

  // Audit
  listAuditLogs: (params?: { action?: string; limit?: number; mine?: boolean }) => {
    const parts = ['limit=' + (params?.limit || 50)]
    if (params?.action) parts.push('action=' + params.action)
    const qs = '?' + parts.join('&')
    const path = params?.mine !== false ? `/api/audit/mine${qs}` : `/api/audit${qs}`
    return request<AuditLog[]>(path)
  },

  // A2A
  sendMessage: (data: { message: { role: string; parts: Array<{type: string; text: string}> } }) =>
    request<{ taskId: string; status: string }>(
      '/a2a/message:send', { method: 'POST', body: JSON.stringify(data) },
    ),

  // Health
  health: () => request<{ status: string }>('/health'),

  // AI
  generateDescription: (data: { name: string; category: string }) =>
    request<{ description: string; model: string }>('/api/ai/generate-description', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Alliance
  listAllianceMembers: () => request<AllianceMember[]>('/api/alliance/members'),
  addAllianceMember: (target_agent_id: string, label?: string) =>
    request<AllianceMember>('/api/alliance/add', {
      method: 'POST',
      body: JSON.stringify({ target_agent_id, label }),
    }),
  removeAllianceMember: (alliance_id: string) =>
    request<void>(`/api/alliance/${alliance_id}`, { method: 'DELETE' }),
  updateAllianceLabel: (alliance_id: string, label: string) =>
    request<{ ok: boolean; label: string }>(`/api/alliance/${alliance_id}/label`, {
      method: 'PATCH',
      body: JSON.stringify({ label }),
    }),
  getAllianceGroups: (alliance_id: string) =>
    request<AllianceGroup[]>(`/api/alliance/${alliance_id}/groups`),
  getAllianceAbilities: (alliance_id: string) =>
    request<AllianceAbility[]>(`/api/alliance/${alliance_id}/abilities`),
  getAllianceSkills: (alliance_id: string) =>
    request<AllianceSkillToken[]>(`/api/alliance/${alliance_id}/skills`),
}
