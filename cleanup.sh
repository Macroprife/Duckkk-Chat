#!/usr/bin/env bash
# 🧹 Duck Chat 半小时清理
# 归档所有活跃对话（前端历史列表变空），数据库完整保留
# 由 cron 每 30 分钟自动执行
# 用法: bash cleanup.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# 1. 轮换云端密码
bash rotate-secret.sh 2>/dev/null || true

# 2. 归档所有未归档对话（数据不删，仅标记 archived_at）
docker compose exec -T postgres \
  psql -U duck -d duck -c "
    UPDATE duck.conversations
    SET archived_at = now()
    WHERE archived_at IS NULL;
  " 2>/dev/null || \
  docker exec myapi-postgres-1 \
  psql -U duck -d duck -c "
    UPDATE duck.conversations
    SET archived_at = now()
    WHERE archived_at IS NULL;
  " 2>/dev/null || true

# 3. 记日志
ARCHIVED=$(docker exec myapi-postgres-1 psql -U duck -d duck -tAc "SELECT COUNT(*) FROM duck.conversations WHERE archived_at IS NOT NULL AND archived_at > now() - interval '1 minute';" 2>/dev/null || echo "?")
echo "$(date '+%Y-%m-%d %H:%M:%S')  archived $ARCHIVED conversations, password rotated" >> /tmp/duck-cleanup.log
