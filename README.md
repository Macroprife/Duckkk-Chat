# 🦆 DuckSay

> 流式 LLM 聊天代理 + PostgreSQL 持久化 + Cloudflare Tunnel 公网访问

支持 **Ollama（本地）** 和 **OpenClaw（云端）** 双模型源，自动记录聊天历史与使用统计。

## 快速开始

```bash
# 1. 配置
cp .env.example .env
# 编辑 .env 填入你的密钥

# 2. 启动
docker compose up -d --build

# 3. 打开浏览器
open http://localhost:8080/ui
```

## 架构

```
手机/浏览器 → Cloudflare Tunnel → Nginx(:8080) → FastAPI(:8000) → PostgreSQL(:5432)
                                                                  ↘ Ollama / OpenClaw
```

## 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 8080 | 反向代理 / 静态资源 |
| FastAPI | 8000 | 聊天 API + UI |
| PostgreSQL | 5432 | 持久化存储 |

## API

| 端点 | 说明 | 鉴权 |
|------|------|------|
| `GET /ui` | 聊天界面 | 无 |
| `POST /chat` | 流式聊天 | 部分需 `x-cloud-key` |
| `GET /models` | 模型列表 | 云端需 key |
| `POST /auth/cloud` | 云端密钥验证 | 限流 10/60s |
| `GET /api/conversations` | 对话历史 | Cookie |
| `GET /api/conversations/{id}` | 对话详情 | Cookie + 所有权 |
| `GET /api/stats/usage` | 用量统计 | Header key |

## 数据库

```sql
duck.sessions      -- 浏览器会话
duck.conversations -- 对话分组
duck.messages      -- 聊天消息
duck.usage_stats   -- Token 用量统计
```

## 密钥轮换

```bash
# 每小时自动轮换云端访问密码
```

## 依赖

- Docker & Docker Compose v2
- Python 3.11+（仅在手动运行时需要）
