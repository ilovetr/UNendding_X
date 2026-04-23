#!/bin/bash
# ============================================================
# 川流/UnendingX 一键安装脚本
# 适用于腾讯轻量应用服务器（Ubuntu/Debian/CentOS）
# ============================================================

set -e

# ─── 颜色 ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ─── 检查 root ───
if [[ $EUID -ne 0 ]]; then
   err "请用 root 用户运行，或加 sudo"
fi

# ─── 参数 ───
DOMAIN="${1:-}"
PORT="${2:-8000}"
POSTGRES_PASSWORD="${3:-$(openssl rand -base64 32)}"
SECRET_KEY="${4:-$(openssl rand -base64 64)}"

# ─── 检测系统 ───
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        err "无法检测操作系统"
    fi
    log "检测到系统: $OS $VERSION_ID"
}

# ─── 安装 Docker ───
install_docker() {
    if command -v docker &> /dev/null; then
        log "Docker 已安装: $(docker --version)"
        return
    fi
    warn "安装 Docker..."

    if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
        apt-get update -qq
        apt-get install -y -qq curl ca-certificates gnupg lsb-release
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif [ "$OS" == "centos" ] || [ "$OS" == "rocky" ] || [ "$OS" == "almalinux" ]; then
        yum install -y -q yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    fi

    systemctl enable docker --now
    log "Docker 安装完成: $(docker --version)"
}

# ─── 配置防火墙 ───
config_firewall() {
    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=443/tcp
        firewall-cmd --reload
    fi
    log "防火墙已配置"
}

# ─── 创建目录结构 ───
create_dirs() {
    mkdir -p /opt/unendingx/{backend,frontend,data,logs}
    cd /opt/unendingx
    log "工作目录: /opt/unendingx"
}

# ─── 写入 docker-compose ───
write_docker_compose() {
    cat > /opt/unendingx/docker-compose.yml << 'EOF'
version: '3.8'

services:
  # PostgreSQL 数据库
  db:
    image: postgres:16-alpine
    container_name: unendingx_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: unendingx
      POSTGRES_USER: unendingx
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./data/db:/var/lib/postgresql/data
    networks:
      - unendingx_net

  # 后端 API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.backend
    container_name: unendingx_backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+asyncpg://unendingx:${POSTGRES_PASSWORD}@db:5432/unendingx
      DATABASE_URL_SYNC: postgresql+psycopg2://unendingx:${POSTGRES_PASSWORD}@db:5432/unendingx
      SECRET_KEY: ${SECRET_KEY}
      FRONTEND_URL: ${FRONTEND_URL:-http://localhost:3000}
    volumes:
      - ./data:/app/data
    depends_on:
      db:
        condition: service_healthy
    networks:
      - unendingx_net

  # 前端
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    container_name: unendingx_frontend
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}
    depends_on:
      - backend
    networks:
      - unendingx_net

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: unendingx_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./data/certs:/etc/nginx/certs:ro
      - ./data/static:/app/static
    depends_on:
      - backend
      - frontend
    networks:
      - unendingx_net

networks:
  unendingx_net:
    driver: bridge
EOF
    log "docker-compose.yml 已写入"
}

# ─── 写入 nginx.conf ───
write_nginx_conf() {
    mkdir -p /opt/unendingx/data/certs /opt/unendingx/data/static

    if [ -n "$DOMAIN" ]; then
        cat > /opt/unendingx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    server_tokens off;

    # ─── 后端 API ───
    server {
        listen 80;
        server_name ${DOMAIN};

        # Let's Encrypt 验证
        location /.well-known/acme-challenge/ {
            root /app/static;
        }

        # 重定向到 HTTPS（如果证书存在）
        location / {
            return 301 https://\$host\$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name ${DOMAIN};

        ssl_certificate /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        client_max_body_size 10M;

        # ─── 前端静态 ───
        location / {
            proxy_pass http://frontend:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_cache_bypass \$http_upgrade;
        }

        # ─── 后端 API ───
        location /api/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # ─── WebSocket ───
        location /ws/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host \$host;
            proxy_read_timeout 86400;
        }

        # ─── A2A 协议端点 ───
        location /a2a/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }

        # ─── 静态文件 ───
        location /static/ {
            alias /app/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
EOF
    else
        # HTTP only 模式
        cat > /opt/unendingx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    server_tokens off;

    # ─── 后端 API ───
    server {
        listen 80;
        server_name _;

        client_max_body_size 10M;

        # ─── 前端静态 ───
        location / {
            proxy_pass http://frontend:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_cache_bypass $http_upgrade;
        }

        # ─── 后端 API ───
        location /api/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # ─── WebSocket ───
        location /ws/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
        }

        # ─── A2A ───
        location /a2a/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
EOF
    fi
    log "nginx.conf 已写入"
}

# ─── 拉取代码 ───
fetch_code() {
    if [ -d /opt/unendingx/.git ]; then
        warn "代码已存在，跳过拉取"
        return
    fi

    local GIT_URL="${GIT_URL:-https://github.com/ilovetr/UNendding_X.git}"
    log "拉取代码: $GIT_URL"

    if command -v git &> /dev/null; then
        git clone "$GIT_URL" /opt/unendingx --depth 1
    else
        err "未安装 git，请先安装: apt install git"
    fi
}

# ─── 写入环境变量 ───
write_env() {
    cat > /opt/unendingx/.env << EOF
# ─── 数据库 ───
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# ─── 安全密钥（生产环境请使用随机字符串）───
SECRET_KEY=${SECRET_KEY}

# ─── 前端 ───
NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
FRONTEND_URL=${FRONTEND_URL:-http://localhost:3000}

# ─── AI 能力（可选）───
# OPENAI_API_KEY=sk-xxx
# SILICONFLOW_API_KEY=xxx
# DEEPSEEK_API_KEY=sk-xxx
EOF
    log ".env 已写入"
    chmod 600 /opt/unendingx/.env
}

# ─── 构建并启动 ───
build_and_start() {
    cd /opt/unendingx

    log "构建 Docker 镜像（首次约需 5-10 分钟）..."
    docker compose build --parallel

    log "启动服务..."
    docker compose up -d

    # 等待后端就绪
    log "等待后端启动..."
    for i in $(seq 1 30); do
        if curl -sf http://localhost:8000/health &>/dev/null; then
            log "后端就绪！"
            break
        fi
        echo -n "."
        sleep 2
    done

    log "服务启动完成！"
}

# ─── 获取 Agent Card ───
show_info() {
    echo ""
    echo "=========================================="
    echo -e "${GREEN} 川流/UnendingX 部署完成！${NC}"
    echo "=========================================="
    if [ -n "$DOMAIN" ]; then
        echo "访问地址: https://${DOMAIN}"
    else
        echo "访问地址: http://81.70.187.125"
    fi
    echo "Agent Card: http://81.70.187.125/api/agent/card"
    echo ""
    echo "常用命令:"
    echo "  查看状态:  cd /opt/unendingx && docker compose ps"
    echo "  查看日志:  cd /opt/unendingx && docker compose logs -f"
    echo "  重启服务:  cd /opt/unendingx && docker compose restart"
    echo "  停止服务:  cd /opt/unendingx && docker compose down"
    echo "  更新代码:  cd /opt/unendingx && git pull && docker compose build && docker compose up -d"
    echo "=========================================="
}

# ─── 主流程 ───
main() {
    log "川流/UnendingX 一键安装脚本"
    log "=========================="

    detect_os
    install_docker
    config_firewall
    create_dirs
    fetch_code
    write_env
    write_docker_compose
    write_nginx_conf
    build_and_start
    show_info
}

main "$@"
