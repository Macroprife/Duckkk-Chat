#!/usr/bin/env bash
set -uo pipefail

# 🦆 Duck Chat — 构建 + 重启（改过代码后运行）
# 用法: bash rebuild-and-run.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}🦆 Duck Chat 重建 + 启动...${NC}"

# ── 1. 构建前端 ──────────────────────────────────────────
echo -e "${YELLOW}📦 安装前端依赖...${NC}"
cd web && npm install --silent 2>&1 | tail -1

echo -e "${YELLOW}🔨 构建前端...${NC}"
npm run build 2>&1 | tail -3
cd "$ROOT"

# ── 2. 构建后端镜像 ──────────────────────────────────────
echo -e "${YELLOW}🐳 构建后端 Docker 镜像...${NC}"
docker compose build api 2>&1 | tail -1

# ── 3. 重启所有容器 ──────────────────────────────────────
echo -e "${YELLOW}🔄 重启服务...${NC}"
docker compose down 2>&1 | tail -1
docker compose up -d 2>&1 | tail -1

# ── 4. 等待服务就绪 ──────────────────────────────────────
echo -n "⏳ 等待服务就绪"
for i in $(seq 1 15); do
  if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
    echo " ✅"
    break
  fi
  echo -n "."
  sleep 1
done

# ── 5. 启动隧道 ──────────────────────────────────────────
echo -e "${YELLOW}☁️  创建 Cloudflare 隧道...${NC}"

# 关旧隧道
docker rm -f duck-tunnel 2>/dev/null || true
kill "$(cat /tmp/duck-tunnel.pid 2>/dev/null)" 2>/dev/null || true

docker run -d --name duck-tunnel --restart unless-stopped \
  --dns 1.1.1.1 --dns-opt use-vc \
  --network host \
  cloudflare/cloudflared:latest tunnel --url http://localhost:8080 >/dev/null 2>&1

echo -n "⏳ 等待隧道建立"
TUNNEL_URL=""
for i in $(seq 1 20); do
  sleep 1
  echo -n "."
  TUNNEL_URL=$(docker logs duck-tunnel 2>&1 | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
  [ -n "$TUNNEL_URL" ] && break
done
echo ""

# ── 6. 轮换密码 ──────────────────────────────────────────
bash rotate-secret.sh 2>/dev/null || true

# ── 7. 输出结果 ──────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🦆 Duck Chat 已就绪！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${CYAN}http://localhost:8080${NC}   (本机)"
echo ""
if [ -n "$TUNNEL_URL" ]; then
  echo -e "  ${GREEN}☁️  手机打开:${NC}"
  echo -e "  ${CYAN}${TUNNEL_URL}${NC}"
  echo ""
fi
PASSWORD=$(cat ~/.duck-secrets/cloud-secret.txt 2>/dev/null || cat /tmp/duck-cloud-secret.txt 2>/dev/null || echo '查看 cat ~/.duck-secrets/cloud-secret.txt')
echo -e "  ${YELLOW}🔑 云端密码: ${PASSWORD}${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
