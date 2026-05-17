#!/usr/bin/env bash
# 🕐 Duck Chat 云端密码轮换
# 每小时执行一次。原子写入 /var/lib/duck-secrets/cloud-secret.txt，
# 容器通过 ro bind mount 读取（写完立即可见）。

set -euo pipefail

SECRETS_DIR="${DUCK_SECRETS_DIR:-$HOME/.duck-secrets}"
SECRET_FILE="$SECRETS_DIR/cloud-secret.txt"
LEGACY_LINK="/tmp/duck-cloud-secret.txt"

mkdir -p "$SECRETS_DIR"
chmod 755 "$SECRETS_DIR"

# 生成 16 位随机密码（小写字母+数字，约 80 位熵）
PASSWORD=$(openssl rand -hex 32 | LC_ALL=C tr -dc 'a-z0-9' | head -c 16)
if [ ${#PASSWORD} -lt 8 ]; then
  echo "❌ 密码生成失败" >&2
  exit 1
fi

# 原子写入：写到临时文件再 rename
TMP="$SECRETS_DIR/.cloud-secret.$$"
umask 077
printf '%s' "$PASSWORD" > "$TMP"
chmod 644 "$TMP"
mv -f "$TMP" "$SECRET_FILE"

# 兼容旧的 /tmp 路径（用户查看密码用）
ln -sf "$SECRET_FILE" "$LEGACY_LINK" 2>/dev/null || cp -f "$SECRET_FILE" "$LEGACY_LINK"
chmod 644 "$LEGACY_LINK" 2>/dev/null || true

echo "$(date '+%H:%M') 新云端密码: $PASSWORD"
