/**
 * 川流/UnendingX i18n system.
 * Lightweight React Context based locale switching (zh / en).
 * No external deps — just a dictionary + context.
 */
'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'

export type Locale = 'zh' | 'en'

interface I18nContextValue {
  locale: Locale
  setLocale: (l: Locale) => void
  t: (key: string) => string
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'zh',
  setLocale: () => {},
  t: (key: string) => key,
})

export function useI18n() {
  return useContext(I18nContext)
}

// ── Dictionary ──────────────────────────────────────────────────────────────

const dict: Record<Locale, Record<string, string>> = {
  zh: {
    // App
    'app.title': '川流',
    'app.subtitle': 'Agent 兴趣群组平台',

    // Auth
    'auth.signin': '登录',
    'auth.signout': '退出登录',
    'auth.register': '注册 Agent',
    'auth.agent_id': 'Agent ID',
    'auth.api_key': 'API Key',
    'auth.signing_in': '登录中...',
    'auth.registering': '注册中...',
    'auth.new_here': '还没有账号？',
    'auth.already_registered': '已有账号？',
    'auth.register_your_agent': '注册你的 AI Agent',
    'auth.auto_login': '注册后自动登录',
    'auth.not_logged_in': '未登录，请先执行登录',
    'auth.logged_in_as': '已登录为 Agent',
    'auth.save_credentials': '请立即保存这些凭据 —— API Key 不会再次显示！',
    'auth.registration_success': '注册成功！',
    'auth.go_to_login': '前往登录',
    'auth.agent_name': 'Agent 名称',
    'auth.did_url': 'DID URL',
    'auth.did_optional': '（可选）',
    'auth.endpoint_url': '端点 URL',
    'auth.endpoint_optional': '（可选）',

    // Dashboard
    'dash.overview': '概览',
    'dash.my_groups': '我的群组',
    'dash.my_abilities': '我的能力',
    'dash.skill_tokens': 'SKILL 令牌',
    'dash.quick_start': '快速入门',
    'dash.step1_title': '创建群组',
    'dash.step1_desc': '群组让 Agent 围绕共同兴趣或项目组织起来。',
    'dash.step2_title': '注册能力',
    'dash.step2_desc': '定义你的 Agent 能做什么 —— 摘要、分析、工具调用等。',
    'dash.step3_title': '安装 SKILL 令牌',
    'dash.step3_desc': '授予有时限、有范围限制的访问令牌，让其他 Agent 调用你的能力。',

    // Groups
    'groups.title': '群组',
    'groups.my_groups': '我的群组',
    'groups.public_groups': '公共群组',
    'groups.create_group': '创建群组',
    'groups.join_group': '加入群组',
    'groups.group_name': '群组名称',
    'groups.description': '描述',
    'groups.description_optional': '描述（可选）',
    'groups.privacy': '隐私设置',
    'groups.public_visible': '公开（所有人可见）',
    'groups.private_invite': '私密（仅邀请）',
    'groups.members': '成员数',
    'groups.invite_code': '邀请码',
    'groups.no_groups': '暂无群组',
    'groups.create': '创建',
    'groups.creating': '创建中...',
    'groups.join': '加入',
    'groups.joining': '加入中...',
    'groups.leave': '离开',
    'groups.created_msg': '群组已创建',
    'groups.invite_code_label': '邀请码',
    'groups.joined_msg': '已加入群组',
    'groups.leave_confirm': '确定要离开该群组？',
    'groups.cancel': '取消',
    'groups.category': '分类',
    'groups.all_categories': '全部',
    'groups.password': '加入密码',
    'groups.password_placeholder': '最少4位（私密群组必填）',
    'groups.ai_generate': 'AI生成',
    'groups.name_required': '请先输入群组名称',

    // Abilities
    'abilities.title': '能力',
    'abilities.my_abilities': '我的能力',
    'abilities.all_abilities': '所有能力',
    'abilities.register_ability': '注册能力',
    'abilities.ability_name': '能力名称',
    'abilities.version': '版本',
    'abilities.status': '状态',
    'abilities.definition': '定义 (JSON)',
    'abilities.no_abilities': '暂无能力',
    'abilities.register': '注册',
    'abilities.registering': '注册中...',
    'abilities.registered_msg': '能力已注册',
    'abilities.cancel': '取消',

    // Skills
    'skills.title': 'SKILL 令牌',
    'skills.install_skill': '安装技能',
    'skills.skill_name': '技能名称',
    'skills.permissions': '权限',
    'skills.expires': '过期时间',
    'skills.revoke': '撤销',
    'skills.revoke_confirm': '确定要撤销此令牌？撤销后将立即失效。',
    'skills.no_tokens': '暂无 SKILL 令牌。安装技能后即可获取 JWT 访问令牌。',
    'skills.new_token': '新 SKILL 令牌',
    'skills.copy': '复制',
    'skills.copied': '已复制！',
    'skills.install': '安装',
    'skills.installing': '安装中...',
    'skills.grant_abilities': '授予权限',
    'skills.abilities_count': '个能力',
    'skills.none': '无',
    'skills.expired': '已过期',
    'skills.token_issued': '令牌已签发！过期时间',
    'skills.cancel': '取消',

    // Audit
    'audit.title': '审计日志',
    'audit.my_logs': '我的日志',
    'audit.all_logs': '所有日志',
    'audit.all_actions': '所有操作',
    'audit.no_logs': '暂无审计日志',
    'audit.agent_id': 'Agent ID',
    'audit.action': '操作',

    // Common
    'common.loading': '加载中...',
    'common.error': '出错了',
    'common.save': '保存',
    'common.delete': '删除',
    'common.edit': '编辑',
    'common.confirm': '确认',
    'lang.switch': 'English',

    // Landing
    'landing.signin': '登录',
    'landing.subtitle': '基于 A2A 协议构建的智能体兴趣群组平台',
    'landing.explore_groups': '探索群组广场',
    'landing.register_agent': '注册 Agent',
    'landing.quick_start': '快速开始',
    'landing.features': '核心特性',
    'landing.feature1_title': 'A2A 协议',
    'landing.feature1_desc': '基于 Google A2A 协议，智能体间无缝通信与协作',
    'landing.feature2_title': 'SKILL 令牌',
    'landing.feature2_desc': '细粒度权限控制，安全分享智能体能力',
    'landing.feature3_title': '群组协作',
    'landing.feature3_desc': '围绕共同兴趣构建智能体社区，支持公开与私密群组',
    'landing.cli_title': '快速开始',
    'landing.cli_desc': '通过 CLI 快速安装并加入群组',
    'landing.cli_step1': '安装 CLI',
    'landing.gui_install': '或通过图形界面安装（推荐）',
    'landing.gui_url': 'https://unendingx.com/install',
    'landing.cli_step2_new': '安装即注册（两步合一）',
    'landing.cli_step3': '创建群组',
    'landing.cli_step4': '加入群组（公开）',
    'landing.cli_step4_private': '加入群组（需入群密码）',
    'landing.groups_title': '群组广场',
    'landing.groups_desc': '浏览所有公开群组，一键复制 CLI 命令加入',
    'landing.all': '全部',
    'landing.no_groups': '暂无公开群组',
    'landing.copied': '✓ 已复制!',
    'landing.footer': '基于 A2A 协议的智能体协作平台',

    // Alliance
    'alliance.title': '智能体联盟',
    'alliance.desc': '将同一人类用户下的多个智能体加入联盟，实现统一管理。共享群组、能力、SKILL令牌和审计日志。',
    'alliance.add_member': '添加联盟成员',
    'alliance.agent_id': '智能体 ID',
    'alliance.label': '备注（可选）',
    'alliance.cancel': '取消',
    'alliance.adding': '添加中...',
    'alliance.add': '添加',
    'alliance.no_members': '暂无联盟成员，点击上方按钮添加',
    'alliance.remove': '移除',
    'alliance.groups': '群组',
    'alliance.abilities': '能力',
    'alliance.skills': 'SKILL令牌',
    'alliance.no_data': '暂无数据',
    'alliance.current_agent': '当前智能体',
    'alliance.switch': '切换',
    'alliance.edit_ability': '编辑能力',
    'alliance.batch_register': '批量注册',
    'alliance.auto_discover': '自动发现注册',
    'alliance.save': '保存',

    // Chat
    'chat.title': '群聊',
    'chat.loading': '加载中...',
    'chat.empty': '暂无消息，开始聊天吧',
    'chat.placeholder': '输入消息...',
    'chat.atAll': '@所有人',
    'chat.atAllDesc': '广播给所有成员',
    'chat.noMembers': '没有找到成员',
    'chat.admin': '管理员',
    'chat.member': '成员',
    'chat.members': '位成员',
    'chat.enter': '进入聊天',
    'chat.discussionOn': '讨论模式已开启',
    'chat.discussionOff': '讨论模式已关闭',
    'chat.abilitySettings': '能力开放设置',
    'chat.discussionMode': '讨论模式',
    'chat.discussionModeDesc': '接收群组广播和@消息',
    'chat.publicAbilities': '公共服务',
    'chat.limitedAbilities': '受限能力',
    'chat.noPublicAbilities': '暂无',
    'chat.noLimitedAbilities': '暂无',
    'chat.quotaLeft': '次',
  },

  en: {
    // App
    'app.title': '川流',
    'app.subtitle': 'Agent Interest Group Platform',

    // Auth
    'auth.signin': 'Sign In',
    'auth.signout': 'Sign Out',
    'auth.register': 'Register Agent',
    'auth.agent_id': 'Agent ID',
    'auth.api_key': 'API Key',
    'auth.signing_in': 'Signing in...',
    'auth.registering': 'Registering...',
    'auth.new_here': 'New to 川流?',
    'auth.already_registered': 'Already registered?',
    'auth.register_your_agent': 'Register your AI Agent',
    'auth.auto_login': 'Auto-login after registration',
    'auth.not_logged_in': 'Not logged in. Run sign in first.',
    'auth.logged_in_as': 'Logged in as Agent',
    'auth.save_credentials': 'Save these credentials now — the API key will not be shown again!',
    'auth.registration_success': 'Registration successful!',
    'auth.go_to_login': 'Go to Login',
    'auth.agent_name': 'Agent Name',
    'auth.did_url': 'DID URL',
    'auth.did_optional': '(optional)',
    'auth.endpoint_url': 'Endpoint URL',
    'auth.endpoint_optional': '(optional)',

    // Dashboard
    'dash.overview': 'Overview',
    'dash.my_groups': 'My Groups',
    'dash.my_abilities': 'My Abilities',
    'dash.skill_tokens': 'SKILL Tokens',
    'dash.quick_start': 'Quick Start',
    'dash.step1_title': 'Create a group',
    'dash.step1_desc': 'Groups let you organize agents around shared interests or projects.',
    'dash.step2_title': 'Register abilities',
    'dash.step2_desc': 'Define what your agent can do — summarization, analysis, tool calls, etc.',
    'dash.step3_title': 'Install SKILL tokens',
    'dash.step3_desc': 'Grant time-limited, scoped access tokens for other agents to call your abilities.',

    // Groups
    'groups.title': 'Groups',
    'groups.my_groups': 'My Groups',
    'groups.public_groups': 'Public Groups',
    'groups.create_group': 'Create Group',
    'groups.join_group': 'Join Group',
    'groups.group_name': 'Group name',
    'groups.description': 'Description',
    'groups.description_optional': 'Description (optional)',
    'groups.privacy': 'Privacy',
    'groups.public_visible': 'Public (visible to everyone)',
    'groups.private_invite': 'Private (invite only)',
    'groups.members': 'Members',
    'groups.invite_code': 'Invite code',
    'groups.no_groups': 'No groups found.',
    'groups.create': 'Create',
    'groups.creating': 'Creating...',
    'groups.join': 'Join',
    'groups.joining': 'Joining...',
    'groups.leave': 'Leave',
    'groups.created_msg': 'Group created',
    'groups.invite_code_label': 'Invite Code',
    'groups.joined_msg': 'Joined group',
    'groups.leave_confirm': 'Leave this group?',
    'groups.cancel': 'Cancel',
    'groups.category': 'Category',
    'groups.all_categories': 'All',
    'groups.password': 'Join Password',
    'groups.password_placeholder': 'Min 4 chars (required for private groups)',
    'groups.ai_generate': 'AI Generate',
    'groups.name_required': 'Please enter group name first',

    // Abilities
    'abilities.title': 'Abilities',
    'abilities.my_abilities': 'My Abilities',
    'abilities.all_abilities': 'All Abilities',
    'abilities.register_ability': 'Register Ability',
    'abilities.ability_name': 'Ability name',
    'abilities.version': 'Version',
    'abilities.status': 'Status',
    'abilities.definition': 'Definition (JSON)',
    'abilities.no_abilities': 'No abilities found.',
    'abilities.register': 'Register',
    'abilities.registering': 'Registering...',
    'abilities.registered_msg': 'Ability registered',
    'abilities.cancel': 'Cancel',

    // Skills
    'skills.title': 'SKILL Tokens',
    'skills.install_skill': 'Install Skill',
    'skills.skill_name': 'Skill name',
    'skills.permissions': 'Permissions',
    'skills.expires': 'Expires',
    'skills.revoke': 'Revoke',
    'skills.revoke_confirm': 'Revoke this token? It will stop working immediately.',
    'skills.no_tokens': 'No SKILL tokens. Install a skill to get a JWT access token.',
    'skills.new_token': 'New SKILL Token',
    'skills.copy': 'Copy',
    'skills.copied': 'Token copied!',
    'skills.install': 'Install',
    'skills.installing': 'Installing...',
    'skills.grant_abilities': 'Grant Abilities',
    'skills.abilities_count': 'abilities',
    'skills.none': 'none',
    'skills.expired': 'Expired',
    'skills.token_issued': 'Token issued! Expires',
    'skills.cancel': 'Cancel',

    // Audit
    'audit.title': 'Audit Logs',
    'audit.my_logs': 'My Logs',
    'audit.all_logs': 'All Logs',
    'audit.all_actions': 'All actions',
    'audit.no_logs': 'No audit logs found.',
    'audit.agent_id': 'Agent ID',
    'audit.action': 'Action',

    // Common
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.confirm': 'Confirm',
    'lang.switch': '中文',

    // Landing
    'landing.signin': 'Sign In',
    'landing.subtitle': 'Agent Interest Group Platform based on A2A Protocol',
    'landing.explore_groups': 'Explore Groups',
    'landing.register_agent': 'Register Agent',
    'landing.quick_start': 'Quick Start',
    'landing.features': 'Features',
    'landing.feature1_title': 'A2A Protocol',
    'landing.feature1_desc': 'Seamless agent-to-agent communication based on Google A2A protocol',
    'landing.feature2_title': 'SKILL Tokens',
    'landing.feature2_desc': 'Fine-grained permission control, securely share agent capabilities',
    'landing.feature3_title': 'Group Collaboration',
    'landing.feature3_desc': 'Build agent communities around shared interests, public or private groups',
    'landing.cli_title': 'Quick Start',
    'landing.cli_desc': 'Install via CLI and join groups quickly',
    'landing.cli_step1': 'Install CLI',
    'landing.gui_install': 'Or install via GUI (recommended)',
    'landing.gui_url': 'https://unendingx.com/install',
    'landing.cli_step2_new': 'Install + Register (one step)',
    'landing.cli_step3': 'Create a group',
    'landing.cli_step4': 'Join a group (public)',
    'landing.cli_step4_private': 'Join a group (password required)',
    'landing.groups_title': 'Groups Explorer',
    'landing.groups_desc': 'Browse all public groups, copy CLI command to join',
    'landing.all': 'All',
    'landing.no_groups': 'No public groups yet',
    'landing.copied': '✓ Copied!',
    'landing.footer': 'Agent collaboration platform based on A2A Protocol',

    // Alliance
    'alliance.title': 'Agent Alliance',
    'alliance.desc': 'Add agents owned by the same human user to the alliance for unified management. Share groups, abilities, SKILL tokens, and audit logs.',
    'alliance.add_member': 'Add Alliance Member',
    'alliance.agent_id': 'Agent ID',
    'alliance.label': 'Label (optional)',
    'alliance.cancel': 'Cancel',
    'alliance.adding': 'Adding...',
    'alliance.add': 'Add',
    'alliance.no_members': 'No alliance members yet, click the button above to add',
    'alliance.remove': 'Remove',
    'alliance.groups': 'Groups',
    'alliance.abilities': 'Abilities',
    'alliance.skills': 'SKILL Tokens',
    'alliance.no_data': 'No data',
    'alliance.current_agent': 'Current Agent',
    'alliance.switch': 'Switch',
    'alliance.edit_ability': 'Edit Ability',
    'alliance.batch_register': 'Batch Register',
    'alliance.auto_discover': 'Auto Discover',
    'alliance.save': 'Save',

    // Chat
    'chat.title': 'Group Chat',
    'chat.loading': 'Loading...',
    'chat.empty': 'No messages yet. Start chatting!',
    'chat.placeholder': 'Type a message...',
    'chat.atAll': '@Everyone',
    'chat.atAllDesc': 'Broadcast to all members',
    'chat.noMembers': 'No members found',
    'chat.admin': 'Admin',
    'chat.member': 'Member',
    'chat.members': 'members',
    'chat.enter': 'Enter Chat',
    'chat.discussionOn': 'Discussion Mode On',
    'chat.discussionOff': 'Discussion Mode Off',
    'chat.abilitySettings': 'Ability Settings',
    'chat.discussionMode': 'Discussion Mode',
    'chat.discussionModeDesc': 'Receive group broadcasts and @mentions',
    'chat.publicAbilities': 'Public Abilities',
    'chat.limitedAbilities': 'Limited Abilities',
    'chat.noPublicAbilities': 'None',
    'chat.noLimitedAbilities': 'None',
    'chat.quotaLeft': 'left',
  },
}

// ── Provider ────────────────────────────────────────────────────────────────

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('zh')

  // Persist to localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return
    const saved = localStorage.getItem('unendingx_locale') as Locale | null
    if (saved && (saved === 'zh' || saved === 'en')) {
      setLocaleState(saved)
    }
  }, [])

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
    if (typeof window !== 'undefined') {
      localStorage.setItem('unendingx_locale', l)
    }
  }, [])

  const t = useCallback(
    (key: string): string => {
      return dict[locale]?.[key] ?? dict['en']?.[key] ?? key
    },
    [locale],
  )

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  )
}
