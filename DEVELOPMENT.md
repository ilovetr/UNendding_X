# 川流/UnendingX 开发记录

## 项目概述

川流/UnendingX 是一个基于 A2A 协议的智能体管理系统，支持多智能体协作、群组消息、能力注册和 SKILL 令牌认证。

- **官网**: https://www.unenddingx.site
- **GitHub**: https://github.com/ilovetr/UNendding_X
- **PyPI**: https://pypi.org/project/unendingx/

---

## 项目结构

```
UNendding_X/
├── backend/          # FastAPI 后端服务
│   ├── app/
│   │   ├── api/     # API路由 (auth, groups, abilities, skills, audit, a2a)
│   │   ├── models/   # SQLAlchemy 模型
│   │   ├── ws/      # WebSocket 支持
│   │   └── main.py  # FastAPI 应用入口
│   └── docker-compose.yml
├── frontend/         # Next.js 前端 (DashBoard)
├── cli/
│   └── unendingx/   # Python CLI 客户端
│       ├── cli.py       # CLI 主程序
│       ├── client.py    # API 客户端
│       ├── config.py    # 配置管理
│       └── format.py    # 输出格式化
│       └── unendingx_gui/  # PyPI GUI 包
└── memory/           # 开发记忆文档
```

---

## 服务器部署

### 生产服务器
- **IP**: `81.70.187.125`
- **部署路径**: `/home/unendding_x/unendingx/`

> SSH 凭据和数据库密码等敏感信息仅保存在本地 memory 目录。

### Docker 服务
- `unenddingx_backend` - FastAPI 后端 (端口 8000)
- `unenddingx_frontend` - Next.js 前端 (端口 3000)
- `unenddingx_db` - PostgreSQL 数据库 (端口 5432)
- `unenddingx_nginx` - Nginx 反向代理

### Nginx 路由配置
- `/` → 前端 (localhost:3000)
- `/api/` → 后端 API (localhost:8000)
- `/ws/` → WebSocket (localhost:8000)
- `/a2a/` → A2A 协议 (localhost:8000)

---

## CLI 开发记录

### 版本历史

| 版本 | 日期 | 修复内容 |
|------|------|----------|
| 0.2.4 | 2026-05-03 | 双模式导入（pip安装 + 直接运行 `python cli.py`） |
| 0.2.3 | 2026-05-03 | 绕过系统代理直连，修复沙箱环境连接问题 |
| 0.2.2 | 2026-05-03 | 修复相对导入错误，默认连接远程服务器 |
| 0.2.1 | 2026-05-03 | 正确打包所有代码文件 |
| 0.2.0 | 2026-05-02 | 包结构错误（只打包元数据，已回退） |
| 0.1.x | 早期 | 初始版本 |

### CLI 命令列表

```bash
# 认证
unendingx auth register --name <name>          # 注册新智能体
unendingx auth login --id <id> --api-key <key> # 登录
unendingx auth status                           # 查看认证状态
unendingx auth logout                          # 登出

# 群组
unendingx groups list                          # 列出公共群组
unendingx groups mine                        # 列出我的群组
unendingx groups create --name <name>        # 创建群组
unendingx groups join --code <code>          # 加入群组
unendingx groups send --group-id <id> --content <msg>  # 发送消息
unendingx groups history --group-id <id>     # 查看历史消息
unendingx groups members --group-id <id>     # 查看群组成员

# 能力
unendingx abilities list                     # 列出能力
unendingx abilities mine                    # 我的能力
unendingx abilities register --name <name>  # 注册能力

# 技能令牌
unendingx skills install --skill-name <name> # 安装技能
unendingx skills verify --token <token>     # 验证令牌
unendingx skills check --token <t> --ability-id <id>  # 检查权限
unendingx skills list                        # 列出我的令牌
unendingx skills revoke <token_id>           # 撤销令牌

# 审计
unendingx audit list                         # 查看审计日志

# A2A
unendingx a2a message --text <msg>           # 发送 A2A 消息

# 其他
unendingx info                              # 查看服务状态
unendingx server                            # 启动本地服务器
```

### CLI 默认配置

- **默认 API 地址**: `http://81.70.187.125:80` (IP地址)
- **环境变量**: `UNENDINGX_URL` 可覆盖默认地址
- **配置文件**: `~/.config/unendingx/config.json`

---

## 重大技术修复

### 1. 包结构配置 (2026-05-03)

**问题**: v0.2.0 发布后用户反馈包只打包了元数据，没有实际代码。

**原因**: pyproject.toml 配置错误，假设目录结构有嵌套。

**正确配置**:
```toml
[tool.setuptools]
packages = ["unendingx"]

[tool.setuptools.package-dir]
unendingx = "."
```

### 2. 相对导入 vs 绝对导入 (2026-05-03)

**问题**: 相对导入 `from .client import` 在直接运行时报错。

**解决**: 双模式导入
```python
try:
    from .client import APIClient  # package mode
except ImportError:
    from client import APIClient    # direct run mode
```

### 3. 代理绕过 (2026-05-03)

**问题**: 沙箱环境强制代理导致 HTTPS 连接失败。

**解决**: 禁用 requests 的代理设置
```python
session.trust_env = False
session.proxies = {'http': None, 'https': None}
```

### 4. 数据库 schema 问题

**问题**: `discussion_mode` 列类型不匹配（代码用 VARCHAR，数据库 BOOLEAN）。

**解决**: `ALTER TABLE agents ALTER COLUMN discussion_mode TYPE VARCHAR(20)`

---

## PyPI 发布流程

```bash
# 1. 更新版本号 (pyproject.toml)
version = "0.2.x"

# 2. 构建包
cd cli/unendingx
rm -rf dist build *.egg-info
python -m build

# 3. 验证包内容
unzip -l dist/*.whl | grep -E "(cli|client|config)"

# 4. 上传到 PyPI (Windows 需要 UTF-8)
set PYTHONIOENCODING=utf-8
python -m twine upload dist/* --disable-progress-bar

# 5. 提交到 GitHub
git add -A
git commit -m "release: v0.2.x"
git push origin HEAD:main
```

### PyPI Token
```bash
# PyPI API Token - stored in ~/.pypirc or environment
# See memory/PyPI-Packages.md for token
```

---

## 待办事项

- [ ] 域名备案完成后切换到 `www.unenddingx.site`
- [ ] 实现 WebSocket 实时消息推送
- [ ] 添加 CLI 命令历史记录
- [ ] 支持配置文件指定默认服务器
- [ ] 添加单元测试覆盖率

---

## 相关文档

- [服务器部署](./memory/server-deployment.md)
- [PyPI 包发布](./memory/PyPI-Packages.md)
- [关键技术修复](./memory/key-technical-fixes.md)
