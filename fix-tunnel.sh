#!/usr/bin/env bash
set -euo pipefail

# 🔧 Duck Chat 隧道修复 + 密码轮换
# 网站打不开时运行此脚本，自动修复并告知信息
# 用法: bash fix-tunnel.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}🔧 Duck Chat 隧道修复中...${NC}"

# ── 1. 检查服务是否活着 ────────────────────────────────
if ! curl -sf http://localhost:8080/health >/dev/null 2>&1; then
  echo -e "${YELLOW}🐳 Duck Chat 未运行，启动容器...${NC}"
  cd "$ROOT" && docker compose up -d 2>&1 | tail -1
  sleep 3
fi

# ── 2. 干掉旧隧道 ──────────────────────────────────────
echo -e "${YELLOW}☠️  关闭旧隧道...${NC}"
docker rm -f duck-tunnel 2>/dev/null || true
kill "$(cat /tmp/duck-tunnel.pid 2>/dev/null)" 2>/dev/null || true

# ── 3. 重建隧道 ──────────────────────────────────────────
echo -e "${YELLOW}☁️  新建 Cloudflare 隧道...${NC}"
docker run -d --name duck-tunnel --restart unless-stopped \
  --dns 1.1.1.1 --dns-opt use-vc \
  --network host \
  cloudflare/cloudflared:latest tunnel --url http://localhost:8080 >/dev/null 2>&1

echo -n "⏳ 等待隧道建立"
URL=""
for i in $(seq 1 20); do
  sleep 1
  echo -n "."
  URL=$(docker logs duck-tunnel 2>&1 | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
  [ -n "$URL" ] && break
done
echo ""

# ── 4. 轮换密码 ──────────────────────────────────────────
bash "$ROOT/rotate-secret.sh" 2>/dev/null || true

# ── 5. 输出 ──────────────────────────────────────────────
PASSWORD=$(cat /etc/duck-secrets/cloud-secret.txt 2>/dev/null || cat /tmp/duck-cloud-secret.txt 2>/dev/null || echo '查看 cat /etc/duck-secrets/cloud-secret.txt')

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ Duck Chat 已恢复！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -n "$URL" ]; then
  echo -e "  ${GREEN}📱 手机浏览器打开:${NC}"
  echo -e "  ${CYAN}${URL}${NC}"
else
  echo -e "  ${YELLOW}⚠️  隧道未获取到地址，手动排查:${NC}"
  echo -e "     ${YELLOW}docker logs duck-tunnel --tail 20${NC}"
fi
echo ""
echo -e "  ${YELLOW}🔑 当前云端密码: ${PASSWORD}${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
