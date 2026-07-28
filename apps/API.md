# Agent 统一 API 规范

> 桌面端 / 网页端 / 小程序 / 任何客户端 共用同一套 API

## 基础信息

- **协议**: HTTPS (小程序要求) / HTTP (桌面/Web)
- **格式**: JSON
- **编码**: UTF-8

## 端点

### POST /api/chat

发送消息，获取 Agent 回复。

**请求**:
```json
{
  "message": "分析项目架构",
  "mode": "act"
}
```

**响应**:
```json
{
  "answer": "项目包含 core/tools/memory/providers 四层...",
  "turns": 3,
  "tool_calls": 5,
  "mode": "act"
}
```

### POST /api/chat/stream

SSE 流式响应。每个 `data:` 行包含 JSON:

```json
{"text": "正在分析..."}
{"text": "发现 3 个模块..."}
{"done": true, "turns": 3, "tool_calls": 5}
```

### GET /api/health

健康检查。

```json
{
  "status": "ok",
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "tools": 7
}
```

### GET /api/tools

列出可用工具。

```json
{
  "tools": [
    {"name": "read_file", "description": "读取文件", "destructive": false},
    {"name": "bash", "description": "执行Shell命令", "destructive": true}
  ]
}
```

## 客户端适配

| 平台 | 调用方式 | 流式 |
|------|---------|:--:|
| 桌面 (PyWebView) | `fetch('/api/chat')` | ✅ |
| 网页 (浏览器) | `fetch('/api/chat/stream')` + SSE | ✅ |
| 小程序 (wx.request) | `wx.request({url:'/api/chat'})` | ❌ |
| 移动端 (React Native) | `fetch` | ✅ |
| 命令行 (curl) | `curl -d '{"message":"..."}' /api/chat` | ❌ |

## 部署

```bash
# 开发环境
python server.py

# 生产环境 (Nginx + Gunicorn)
gunicorn -w 4 -b 127.0.0.1:5000 agent.server:app

# Docker
docker build -t agent . && docker run -p 5000:5000 agent
```
