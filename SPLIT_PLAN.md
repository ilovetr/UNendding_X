# 代码拆分方案：官网 vs 本地插件 GUI

## 拆分状态：✅ 已完成

---

## 最终结构

```
UNendding_X/
├── frontend/                    ← 官网（已部署在 81.70.187.125）
│   ├── src/app/
│   │   ├── page.tsx            ← Landing（Hero + 特性 + 群组广场 + CLI指南）
│   │   ├── login/              ← 登录页（Agent ID + API Key 表单）
│   │   └── register/           ← 注册页（新增智能体）
│   ├── src/lib/               ← i18n + api client
│   └── package.json
│
├── frontend-gui/              ← 本地插件 GUI（pip install unendingx-gui）
│   ├── src/app/
│   │   ├── page.tsx            ← 根路由 → redirect to /dashboard
│   │   ├── login/              ← 登录页（显示已注册智能体列表）
│   │   └── dashboard/          ← 完整 Dashboard（abilities/alliance/audit/groups/skills）
│   ├── src/lib/               ← i18n + api client
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── postcss.config.js
│
├── cli/
│   ├── unendingx/             ← pip install unendingx（自动注册）
│   │   ├── cli.py              ← 首次命令时自动注册（已移除 init 命令）
│   │   ├── client.py
│   │   ├── config.py
│   │   └── pyproject.toml
│   │
│   └── unendingx_gui/          ← pip install unendingx-gui（自动启动 GUI）
│       ├── cli.py              ← 指向 frontend-gui/（已更新）
│       ├── pyproject.toml      ← 依赖 unendingx>=0.1.0
│       └── README.md
│
├── backend/                    ← FastAPI 后端（已部署在 81.70.187.125）
└── deploy/                     ← 部署配置
```

---

## 变更记录

### 1. `frontend-gui/` 新建（2026-04-24）
- ✅ 复制 `frontend/` 的 Next.js 配置（package.json, next.config.js, tailwind.config.ts, tsconfig.json, postcss.config.js）
- ✅ 复制 Dashboard 完整代码（abilities, alliance, audit, groups, skills）
- ✅ 新建 login 页面（显示已注册智能体列表，点击进入 Dashboard）
- ✅ 删除 register 页面（注册改为自动）
- ✅ 删除 landing 页面（本地 GUI 不需要）
- ✅ 根路由 `/` → redirect to `/dashboard`

### 2. `unendingx` CLI（cli/unendingx/cli.py）
- ✅ **移除** `unendingx init` 命令
- ✅ **新增** 首次命令时自动注册：检查 access_token，不存在则调用 `/api/auth/init`
- ✅ 注册信息：name = `{hostname}-cli`，device_id = 硬件 UUID
- ✅ 保存到 `~/.config/unendingx/config.json`

### 3. `unendingx-gui` CLI（cli/unendingx_gui/cli.py）
- ✅ **更新** frontend 路径：`frontend/` → `frontend-gui/`
- ✅ 自动注册逻辑保留（name = `{hostname}-gui`）
- ✅ 指向 `frontend-gui/` 目录启动 Next.js dev server

### 4. 官网 Landing 页面（frontend/src/app/page.tsx）
- ✅ 移除 `unendingx init` 命令引用（CLI 指南部分）
- ✅ 保留 `pip install unendingx` 和 `pip install unendingx-gui`

---

## 使用方式

### pip install unendingx
```bash
pip install unendingx
unendingx groups list    # 首次运行自动注册
```

### pip install unendingx-gui
```bash
pip install unendingx-gui
unendingx-gui           # 自动注册 + 启动本地 GUI
```

### 官网（已部署）
- URL: `http://81.70.187.125`
- 包含：Landing + 登录 + 注册 + 群组广场

---

## 技术说明

### 自动注册流程

**unendingx CLI**：
1. 运行任意命令 → `cli()` 检查 `config.get("access_token")`
2. 无 token → 调用 `/api/auth/init` → `save_auth()` 保存
3. 打印 "✅ Registered as: xxx"

**unendingx-gui CLI**：
1. `gui()` 命令 → 检查已注册状态
2. 未注册 → 调用 `/api/auth/init` → `save_auth()`
3. 启动 Next.js dev server（`frontend-gui/`）
4. 打开浏览器 → login 页面显示本机智能体

### Login 页面行为（frontend-gui）

1. **首次访问**：localStorage 无数据 → 显示"本机智能体"卡片（CLI 自动注册的）→ 点击进入 Dashboard
2. **后续访问**：读取 `unendingx_last_used_agent` → 自动 redirect to /dashboard
3. **多智能体切换**：Dashboard 侧边栏有 agent switcher（已有实现）
