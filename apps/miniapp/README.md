# Agent 小程序 · 微信小程序版

## 使用方式

将 `apps/miniapp/` 目录导入微信开发者工具即可。

## 架构

```
┌──────────────────────────────┐
│   微信小程序 (WXML/WXSS/JS)   │
│   apps/miniapp/              │
├──────────────────────────────┤
│   Agent API (Flask)          │
│   POST /api/chat             │
│   POST /api/chat/stream      │
│   GET  /api/health           │
└──────────────────────────────┘
```

## 文件结构

```
apps/miniapp/
├── app.json          # 小程序配置
├── app.wxss           # 全局样式
├── pages/
│   └── chat/
│       ├── chat.wxml   # 聊天界面
│       ├── chat.wxss   # 聊天样式
│       └── chat.js     # 聊天逻辑
└── utils/
    └── api.js          # API 调用封装
```

## 部署

1. 后端部署到服务器（需 HTTPS）
2. 修改 `utils/api.js` 中的 API 地址
3. 在微信公众平台注册小程序
4. 导入微信开发者工具 → 上传

## 后端要求
- HTTPS 域名（微信小程序要求）
- `/api/chat` 端点可用
- 建议用 Nginx 反代 Flask
