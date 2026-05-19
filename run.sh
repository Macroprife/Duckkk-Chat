#!/usr/bin/env bash
set -uo pipefail

# 🦆 Duck Chat — 直接启动（代码没改时运行）
# 用法: bash run.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}🦆 Duck Chat 启动中...${NC}"

# ── 1. 启动 Docker 容器 ─────────────────────────────────
echo -e "${YELLOW}🐳 启动容器...${NC}"
docker compose up -d 2>&1 | tail -1

echo -n "⏳ 等待服务就绪"
for i in $(seq 1 15); do
  if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
    echo " ✅"
    break
  fi
  echo -n "."
  sleep 1
done

# ── 2. 启动隧道 ──────────────────────────────────────────
echo -e "${YELLOW}☁️  创建 Cloudflare 隧道...${NC}"

# 关旧隧道
docker rm -f duck-tunnel 2>/dev/null || true
kill "$(cat /tmp/duck-tunnel.pid 2>/dev/null)" 2>/dev/null || true

docker run -d --name duck-tunnel --restart unless-stopped \
  --network host \
  cloudflare/cloudflared:latest tunnel --url http://localhost:8080 --protocol http2 >/dev/null 2>&1

echo -n "⏳ 等待隧道建立"
TUNNEL_URL=""
for i in $(seq 1 20); do
  sleep 1
  echo -n "."
  TUNNEL_URL=$(docker logs duck-tunnel 2>&1 | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
  [ -n "$TUNNEL_URL" ] && break
done
echo ""

# ── 3. 轮换密码 ──────────────────────────────────────────
bash rotate-secret.sh 2>/dev/null || true

# ── 4. 输出结果 ──────────────────────────────────────────
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
PASSWORD=$(cat ./secrets/cloud-secret.txt 2>/dev/null || echo '未设置')
echo -e "  ${YELLOW}🔑 云端密码: ${PASSWORD}${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
