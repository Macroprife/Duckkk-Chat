# 🦆 Duck Chat

LLM 流式代理 + 浏览器聊天界面。支持 Ollama（本地）和 OpenClaw（云端），
**内置 PostgreSQL 持久化存储**。

**一句话部署：**

```bash
git clone <仓库地址> duck-chat && cd duck-chat
cp .env.example .env   # 编辑 .env 填入 DEEPSEEK_API_KEY
./start.sh             # docker compose up -d --build
```

浏览器打开 `http://localhost:8080/ui` 开始聊天。

---

## 🌟 功能特性

- **双模型源** – Ollama 本地模型 + OpenClaw 云端模型
- **流式输出** – SSE 实时显示 token
- **云端认证** – 云端模型需要密钥访问
- **PostgreSQL 持久化** – 消息历史、会话信息、使用统计自动入库
- **历史查看 API** – 查询过去的对话记录
- **使用统计 API** – 按模型聚合 token 消耗统计

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **必填** |
| `PORT` | `8080` | 对外暴露端口 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名 |
| `DEEPSEEK_TIMEOUT` | `60` | 请求超时（秒） |
| `CLOUD_AUTH_KEY` | `changeme` | 云端模型访问密钥 |
| `DATABASE_URL` | `postgresql://duck:duck@localhost:5432/duck` | PostgreSQL 连接串 |

## 数据库 schema

| 表 | 作用 |
|------|------|
| `duck.sessions` | 浏览器会话 / 客户端信息 |
| `duck.conversations` | 每次对话（用户一次聊天请求） |
| `duck.messages` | 单条消息（user / assistant） |
| `duck.usage_stats` | Token 使用统计（用于分析） |

自动建表，无需手动干预。

## API 端点

| 路径 | 方法 | 说明 |
|------|------|------|
| `/ui` | GET | 聊天界面 |
| `/chat` | POST | 发送消息（流式返回） |
| `/models` | GET | 列出可用模型 |
| `/auth/cloud` | POST | 云模型密钥验证 |
| `/api/conversations` | GET | 当前会话的对话列表 |
| `/api/conversations/{id}` | GET | 某次对话的完整消息 |
| `/api/stats/usage` | GET | Token 使用统计 |
| `/health` | GET | 健康检查 |

## 无 Docker 环境

```bash
# 需要本地运行 PostgreSQL（或远程）
pip install -r requirements.txt
DATABASE_URL=postgresql://... uvicorn app:app --reload --host 0.0.0.0
```

## 架构支持

- ✅ amd64（Intel / AMD）
- ✅ arm64（Apple Silicon Mac、树莓派、Oracle ARM）

## 常用命令

```bash
docker compose up -d         # 启动
docker compose down          # 停止（数据库数据保留在卷中）
docker compose down -v       # 💥 停止并删除数据库数据
docker compose logs -f       # 看日志
docker compose restart       # 重启
docker compose pull          # 拉取 nginx 新镜像
```

## 数据库查看

```bash
# 进入 PostgreSQL 容器查看数据
docker exec -it duck-myapi-postgres-1 psql -U duck -d duck -c "SELECT * FROM duck.usage_stats ORDER BY created_at DESC LIMIT 10;"
```
