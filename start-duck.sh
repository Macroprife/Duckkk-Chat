#!/usr/bin/env bash
set -uo pipefail

# 🦆 Duck Chat — 一键启动脚本
# 启动 Docker 容器并创建 Cloudflare 快速隧道
# 用法: bash start-duck.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}🦆 Duck Chat 启动中...${NC}"

# ── 1. 检查 cloudflared ──────────────────────────────────
CLOUDFLARED="/tmp/cloudflared"
if [ ! -f "$CLOUDFLARED" ]; then
  echo -e "${YELLOW}📥 下载 cloudflared...${NC}"
  curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$CLOUDFLARED"
  chmod +x "$CLOUDFLARED"
  echo -e "${GREEN}✅ cloudflared 已安装${NC}"
fi

# ── 2. 启动 Docker 容器 ─────────────────────────────────
echo -e "${YELLOW}🐳 启动 Duck Chat 容器...${NC}"
docker compose up -d 2>&1

echo -n "⏳ 等待 Duck Chat 就绪"
for i in $(seq 1 15); do
  if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
    echo " ✅"
    break
  fi
  echo -n "."
  sleep 1
done

# ── 3. 启动 Cloudflare 快速隧道 ────────────────────────
echo -e "${YELLOW}☁️  创建 Cloudflare 快速隧道...${NC}"

# 后台运行隧道，日志写文件
TUNNEL_LOG="/tmp/duck-tunnel-$$.log"
nohup "$CLOUDFLARED" tunnel --url http://localhost:8080 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# 保存 PID
echo "$TUNNEL_PID" > /tmp/duck-tunnel.pid

# 等待隧道获取 Cloudflare 分配的 URL
echo -n "⏳ 等待隧道建立"
TUNNEL_URL=""
for i in $(seq 1 30); do
  sleep 1
  echo -n "."
  TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1 || true)
  if [ -n "$TUNNEL_URL" ]; then
    break
  fi
done
echo ""

# ── 4. 保存并输出结果 ─────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  🦆 Duck Chat 已就绪！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${CYAN}http://localhost:8080/ui${NC}   (本机)"
echo ""

if [ -n "$TUNNEL_URL" ]; then
  FULL_URL="${TUNNEL_URL}/ui"
  echo -e "  ${GREEN}☁️  手机访问:${NC}"
  echo -e "  ${CYAN}${FULL_URL}${NC}"
  echo ""
  echo -e "  ${YELLOW}📝 此域名限时有效，关闭终端后失效${NC}"
  echo -e "  ${YELLOW}   重启后重新运行此脚本获取新地址${NC}"

  # 追加到历史记录
  LOGFILE="/tmp/duck-tunnel-history.log"
  echo "$(date '+%Y-%m-%d %H:%M:%S') → ${FULL_URL}" >> "$LOGFILE"
else
  echo -e "  ${YELLOW}⚠️  隧道建立超时${NC}"
  echo -e "     查看日志: cat ${TUNNEL_LOG}"
fi

echo ""
echo -e "  停止:  ${YELLOW}make stop${NC}  或  ${YELLOW}docker compose down${NC}"
echo -e "  历史:  ${YELLOW}cat /tmp/duck-tunnel-history.log${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
