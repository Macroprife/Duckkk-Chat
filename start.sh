#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "🦆 Duck Chat — 一键启动"
echo "──────────────────────"

# ── 1. 检查 .env ────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "📄 未发现 .env，从 .env.example 创建……"
    cp .env.example .env
    echo "⚠️  请编辑 .env 填入你的 DEEPSEEK_API_KEY"
    echo "   然后重新运行 ./start.sh"
    exit 0
  else
    echo "❌ 缺少 .env 和 .env.example"
    exit 1
  fi
fi

# 检查 Key 是否还是占位符
if grep -q "your_key_here" .env 2>/dev/null; then
  echo "❌ .env 中的 DEEPSEEK_API_KEY 仍是占位符"
  echo "   请编辑 .env 填入真实 Key"
  exit 1
fi

# ── 2. 检查 Docker ──────────────────────────
if ! command -v docker &>/dev/null; then
  echo "❌ 未安装 Docker"
  echo "   安装：https://docs.docker.com/engine/install/"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "❌ 需要 docker compose（v2）"
  exit 1
fi

# ── 3. 启动 ──────────────────────────────────
echo "🚀 构建并启动……"
docker compose up -d --build

echo ""
echo "✅ Duck Chat 已启动"
echo "   浏览器打开 → http://localhost:${PORT:-8080}/ui"
echo ""
echo "📋 常用命令"
echo "   docker compose logs -f    查看日志"
echo "   docker compose down       停止"
echo "   docker compose restart    重启"
echo "   docker compose pull       更新镜像"
