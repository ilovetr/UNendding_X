# 川流/UnendingX 腾讯轻量云部署指南

## 前提条件

- 腾讯轻量应用服务器（Ubuntu 20.04+ / Debian 11+ / CentOS 7+）
- SSH 密钥已配置到服务器
- 域名（可选，启用 HTTPS）

---

## 方式一：一键安装（推荐）

### 第一步：确认 SSH 能连上

```bash
ssh -i "你的密钥.pem" root@81.70.187.125
```

> 如果连不上，请先在腾讯云控制台 → 轻量应用服务器 → 找到实例 → 点击「远程登录」，用 VNC 方式登录服务器，然后手动上传公钥：
> ```bash
> mkdir -p ~/.ssh && chmod 700 ~/.ssh
> # 把本地的 ~/.ssh/unendingx.pem 对应的公钥内容粘贴到这里
> nano ~/.ssh/authorized_keys
> chmod 600 ~/.ssh/authorized_keys
> ```

### 第二步：上传安装脚本

把 `1-install.sh` 上传到服务器：

```bash
# 方法 A：用 scp 上传（在你的本地终端执行）
scp -i "E:\工作\AI\agent_grounp\UNendding_X.pem" E:\工作\AI\agent_grounp\deploy\1-install.sh root@81.70.187.125:/tmp/

# 方法 B：复制文件内容，在服务器上 vi 创建
```

### 第三步：运行安装

```bash
# SSH 登录服务器
ssh -i "你的密钥.pem" root@81.70.187.125

# 运行安装
chmod +x /tmp/1-install.sh
cd /tmp && bash 1-install.sh
```

### 参数说明

```bash
# 基本用法（HTTP 模式）
bash 1-install.sh

# 带域名（HTTPS 模式）
bash 1-install.sh yourdomain.com

# 完全自定义
bash 1-install.sh yourdomain.com 8000 "你的数据库密码" "你的密钥"
```

---

## 方式二：手动分步安装

### 1. 安装 Docker

```bash
# Ubuntu/Debian
apt-get update && apt-get install -y docker.io docker-compose

# CentOS
yum install -y docker docker-compose
systemctl enable docker --now
```

### 2. 克隆代码

```bash
cd /opt
git clone https://github.com/ilovetr/UNendding_X.git unendingx
cd unendingx
```

### 3. 配置环境变量

```bash
cp backend/.env.example .env
nano .env
# 修改 SECRET_KEY 为随机字符串
```

### 4. 启动

```bash
docker compose -f docker-compose.yml up -d --build
docker compose ps   # 查看状态
docker compose logs -f  # 查看日志
```

---

## 安装后验证

```bash
# 检查容器状态
docker compose ps

# 检查后端健康
curl http://localhost:8000/health

# 检查 Agent Card
curl http://localhost:8000/api/agent/card

# 检查前端
curl http://localhost:3000
```

---

## HTTPS 配置（可选）

安装 [acme.sh](https://github.com/acmesh-official/acme.sh) 自动申请 Let's Encrypt 证书：

```bash
# 在服务器上执行
curl https://get.acme.sh | sh
~/.acme.sh/acme.sh --issue -d yourdomain.com --nginx /etc/nginx/nginx.conf

# 复制证书
mkdir -p /opt/unendingx/data/certs
~/.acme.sh/acme.sh --install-cert -d yourdomain.com \
  --key-file /opt/unendingx/data/certs/privkey.pem \
  --fullchain-file /opt/unendingx/data/certs/fullchain.pem

# 重启 Nginx
docker compose -f /opt/unendingx/docker-compose.yml restart nginx
```

---

## 常用维护命令

| 操作 | 命令 |
|------|------|
| 查看日志 | `docker compose -f /opt/unendingx/docker-compose.yml logs -f` |
| 重启服务 | `docker compose -f /opt/unendingx/docker-compose.yml restart` |
| 更新代码 | `cd /opt/unendingx && git pull && docker compose build && docker compose up -d` |
| 停止服务 | `docker compose -f /opt/unendingx/docker-compose.yml down` |
| 备份数据库 | `docker compose -f /opt/unendingx/docker-compose.yml exec db pg_dump -U unendingx unendingx > backup.sql` |
| 进入容器 | `docker compose -f /opt/unendingx/docker-compose.yml exec backend bash` |

---

## 访问地址

安装完成后：

- **前端（官网/Dashboard）**: `http://81.70.187.125`
- **后端 API**: `http://81.70.187.125/api/`
- **Agent Card**: `http://81.70.187.125/api/agent/card`

---

## 故障排查

### 容器启动失败
```bash
docker compose -f /opt/unendingx/docker-compose.yml logs backend
docker compose -f /opt/unendingx/docker-compose.yml logs frontend
```

### 端口被占用
```bash
# 检查 80 端口
netstat -tlnp | grep :80
# 或
ss -tlnp | grep :80
```

### 数据库连接失败
```bash
docker compose -f /opt/unendingx/docker-compose.yml exec db psql -U unendingx -d unendingx -c "SELECT 1;"
```

### 清理重装
```bash
docker compose -f /opt/unendingx/docker-compose.yml down -v
rm -rf /opt/unendingx/data
docker compose -f /opt/unendingx/docker-compose.yml up -d --build
```
