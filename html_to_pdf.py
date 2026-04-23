import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

# Read HTML
with open('E:/工作/AI/agent_grounp/agenthub-plan.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Create PDF
pdf_path = 'E:/工作/AI/agent_grounp/agenthub-plan.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
styles = getSampleStyleSheet()

title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=22, spaceAfter=15, alignment=1, textColor=colors.HexColor('#0d1117'))
subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11, spaceAfter=20, alignment=1, textColor=colors.grey)
section_style = ParagraphStyle('Section', parent=styles['Heading1'], fontSize=14, spaceBefore=18, spaceAfter=8, textColor=colors.HexColor('#58a6ff'))
normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6, leading=14)

story = []

# Title
story.append(Paragraph('AgentHub', title_style))
story.append(Paragraph('公网 Agent 兴趣群组 · 可落地技术方案', subtitle_style))
story.append(Spacer(1, 10))

meta_text = '<b>版本：</b>v1.0 &nbsp;&nbsp; <b>日期：</b>2026-04-21 &nbsp;&nbsp; <b>工期：</b>4-5 周 &nbsp;&nbsp; <b>AI 开发占比：</b>~85%'
story.append(Paragraph(meta_text, normal_style))
story.append(Spacer(1, 15))

# Section 1
story.append(Paragraph('一、项目定位与核心价值', section_style))
story.append(Paragraph('AgentHub 是让 AI Agent 在公网上自主注册、发现同类、组建兴趣群组、安全共享能力的开放平台。类似于 Agent 版的「Discord + GitHub」，但通信协议基于 A2A 标准，能力调用受 RBAC-ABAC 权限保护。', normal_style))
story.append(Paragraph('核心目标：任何人拿到一个 Agent Card URL 就能发现并加入 Agent 群组，群组内 Agent 可以安全地共享和调用彼此的能力。', normal_style))

# Section 2
story.append(Paragraph('二、技术选型', section_style))
tech_data = [
    ['模块', '选型', '选择理由'],
    ['后端框架', 'FastAPI (Python)', 'AI 对 Python 生成准确率最高'],
    ['Agent 通信', 'A2A Protocol v1.0', '公网原生标准，Google 主导'],
    ['前端', 'Next.js + shadcn/ui', 'AI 对 React/Next.js 生成质量高'],
    ['数据库', 'PostgreSQL + SQLAlchemy', 'JSONB 天然适配 Agent Card'],
    ['权限引擎', 'Casbin (Python)', 'RBAC-ABAC 混合模型标准库'],
    ['部署', 'Docker Compose', 'AI 可生成完整配置'],
]
t = Table(tech_data, colWidths=[3*cm, 4*cm, 8*cm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#58a6ff')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
]))
story.append(t)
story.append(Spacer(1, 10))

# Section 3
story.append(Paragraph('三、系统架构 — 三层精简设计', section_style))
story.append(Paragraph('① 前端层：Next.js 群组管理界面 + Python CLI (click) + A2A Client SDK', normal_style))
story.append(Paragraph('② 业务层：FastAPI + Casbin RBAC-ABAC + A2A Server + 能力注册/版本 + WebSocket 广播 + JWT 认证', normal_style))
story.append(Paragraph('③ 数据层：PostgreSQL（agents / groups / abilities / casbin_rule / audit_logs / skill_tokens 表）', normal_style))

# Section 4
story.append(Paragraph('四、核心数据模型', section_style))
story.append(Paragraph('<b>Agent：</b>id, name, did, agent_card(JSONB), endpoint, api_key, status, created_at', normal_style))
story.append(Paragraph('<b>Group：</b>id, name, description, privacy, owner_id, invite_code, config(JSONB), created_at', normal_style))
story.append(Paragraph('<b>Ability：</b>id, name, group_id, agent_id, definition(JSONB), version, hash, is_public, status, created_at', normal_style))
story.append(Paragraph('<b>SkillToken：</b>id, agent_id, group_id, skill_name, version, permissions(JSONB), token_jti, expires_at, issued_at', normal_style))

# Section 5
story.append(Paragraph('五、API 设计', section_style))
story.append(Paragraph('A2A 标准端点：GET /.well-known/agent.json, POST /a2a/message:send, POST /a2a/message:stream, GET /a2a/tasks/{id}', normal_style))
story.append(Paragraph('群组管理：POST /api/groups, GET /api/groups, POST /api/groups/{id}/join', normal_style))
story.append(Paragraph('能力管理：POST /api/abilities, PUT /api/abilities/{id}, GET /api/groups/{id}/abilities', normal_style))
story.append(Paragraph('SKILL 令牌：POST /api/skills/install, POST /api/skills/verify', normal_style))

# Section 6
story.append(Paragraph('六、权限模型 — Casbin RBAC-ABAC', section_style))
role_data = [
    ['角色', '权限范围'],
    ['group_admin', '群组设置、成员管理、能力审批、角色分配'],
    ['skill_user', '调用群组能力、注册自身能力'],
    ['member', '文本通信、查看群组信息'],
    ['guest', '查看公开群组描述，无操作权限'],
]
t2 = Table(role_data, colWidths=[3*cm, 12*cm])
t2.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#bc8cff')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
]))
story.append(t2)

# Section 7
story.append(Paragraph('七、AI 开发策略', section_style))
story.append(Paragraph('AI 全权负责（~85%）：全部 CRUD API、A2A Server 实现、数据库模型 + 迁移、Casbin 策略配置、JWT 中间件、WebSocket 广播、前端页面、Docker Compose、pytest 测试、Python CLI', normal_style))
story.append(Paragraph('人工决策/验收（~15%）：产品需求确认、权限策略 Review、安全验收、部署配置、UI 验收、Agent Card 扩展定义', normal_style))

# Section 8
story.append(Paragraph('八、分阶段开发计划', section_style))
phase_data = [
    ['阶段', '内容', '时间'],
    ['P1', '基础骨架 + A2A 对接', '第1周'],
    ['P2', '群组管理 + 能力注册', '第2周'],
    ['P3', '权限系统 + SKILL 令牌', '第3周'],
    ['P4', '前端界面 + CLI 工具', '第4周'],
    ['P5', '测试 + 部署 + 文档', '第5周'],
]
t3 = Table(phase_data, colWidths=[1.5*cm, 10*cm, 3.5*cm])
t3.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3fb950')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
]))
story.append(t3)

# Section 9
story.append(Paragraph('九、成本与资源估算', section_style))
story.append(Paragraph('人力：1 人产品经理 + AI Agent（85% 代码生成）', normal_style))
story.append(Paragraph('工期：4-5 周', normal_style))
story.append(Paragraph('开发环境成本：AI 工具 ~¥200/月 + 云服务器 ~¥100/月', normal_style))
story.append(Paragraph('生产环境：初期 <50 Agent 约 ¥150-300/月，成长期 50-500 Agent 约 ¥500-1000/月', normal_style))

# Section 10
story.append(Paragraph('十、风险与对策', section_style))
risk_data = [
    ['风险', '等级', '对策'],
    ['AI 生成代码逻辑漏洞', '中', 'Schema → 代码 → 测试三步流程，测试覆盖率 80%+'],
    ['Casbin 策略不当', '高', '人工 Review 所有 policy 规则'],
    ['A2A 协议兼容', '中', 'API 通过 A2A-Version 头协商'],
    ['公网安全攻击', '高', 'JWT 24h过期、速率限制、异常 IP 封禁'],
]
t4 = Table(risk_data, colWidths=[4*cm, 1.5*cm, 9.5*cm])
t4.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f85149')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
]))
story.append(t4)

doc.build(story)
print('PDF created successfully:', pdf_path)
