#!/usr/bin/env bash
# 🔧 Duck Chat — 隧道修复脚本
# 网站打不开时运行此脚本即可恢复
# 用法: bash fix-tunnel.sh

set -euo pipefail

echo "🔧 Duck Chat 隧道修复中..."

# 1. 检查 Duck Chat 是否运行
if ! curl -sf http://localhost:8080/ui >/dev/null 2>&1; then
  echo "🐳 启动 Duck Chat 容器..."
  cd "$(dirname "$0")" && docker compose up -d 2>&1 | tail -1
  sleep 3
fi

# 2. 清理旧隧道
echo "☠️  关闭旧隧道..."
docker rm -f duck-tunnel 2>/dev/null || true

# 3. 重建隧道
# --dns-opt use-vc 强制 TCP DNS，绕过运营商/网络 UDP DNS 劫持
echo "☁️  新建 Cloudflare 隧道..."
docker run -d --name duck-tunnel --restart unless-stopped \
  --dns 1.1.1.1 --dns-opt use-vc \
  --network host \
  cloudflare/cloudflared:latest tunnel --url http://localhost:8080 >/dev/null 2>&1

# 4. 等待隧道建立
echo -n "⏳ 等待隧道建立"
URL=""
for i in $(seq 1 20); do
  sleep 1
  echo -n "."
  URL=$(docker logs duck-tunnel 2>&1 | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)
  [ -n "$URL" ] && break
done
echo ""

# 5. 输出结果
if [ -n "$URL" ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  ✅ Duck Chat 已恢复！"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "  手机打开:"
  echo "  ${URL}/ui"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
  echo ""
  echo "❌ 隧道建立超时，排查命令："
  echo "   docker logs duck-tunnel --tail 20"
fi
