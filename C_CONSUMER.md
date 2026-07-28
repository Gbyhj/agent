# Agent C 端接入方案

> 从开发者工具 → 面向消费者的 AI 产品

---

## 完整 Checklist

### 🔴 必须有（不上线不行）

| # | 需求 | 现状 | 方案 |
|:--:|------|:--:|------|
| 1 | **用户注册/登录** | ❌ | 微信登录 (小程序) / 手机号 / 邮箱 |
| 2 | **多用户数据隔离** | ❌ | user_id 分区，每个用户独立记忆/会话 |
| 3 | **生产服务器** | ❌ | Gunicorn + Nginx + HTTPS |
| 4 | **数据库** | ❌ | SQLite → PostgreSQL |
| 5 | **API 限流** | ❌ | 每用户每分钟 N 次 |
| 6 | **费用控制** | ❌ | 每用户每日预算 ¥0.5-5 |
| 7 | **错误处理** | ⚠️ | 友好中文错误提示，非原始 traceback |

### 🟡 应该有（体验加分）

| # | 需求 | 方案 |
|:--:|------|------|
| 8 | 对话历史 | 用户可查看/搜索/删除历史对话 |
| 9 | 新手引导 | 首次使用 3 步引导：选择场景 → 示例任务 → 开始使用 |
| 10 | 消息推送 | 微信模板消息通知任务完成 |
| 11 | 使用统计 | 用户可看自己的 Token/费用/任务统计 |
| 12 | 反馈系统 | 每次回答后 👍👎 + 文字反馈 |

### 🟢 最好有（竞争力）

| # | 需求 | 方案 |
|:--:|------|------|
| 13 | 付费体系 | 免费额度 + 会员订阅 (¥9.9/月) |
| 14 | 管理后台 | 用户管理、用量监控、内容审核 |
| 15 | 隐私政策/TOS | 法务文件 |
| 16 | 内容安全 | 敏感词过滤 + 输出审核 |
| 17 | 分享功能 | 生成分享卡片，小程序转发 |
| 18 | 离线模式 | 本地小模型兜底 |

---

## 技术架构升级

```
当前:  Flask dev server → 单用户 → 文件存储
                                ↓
C端:   Nginx → Gunicorn → Flask → PostgreSQL + Redis
              ↓
         HTTPS + CDN
              ↓
     ┌───────┼───────┐
     ▼       ▼       ▼
   微信小程序  Web    API (第三方接入)

用户系统:
  ┌─ 微信授权登录 (小程序)
  ├─ 手机号验证码
  └─ JWT Token 鉴权

数据隔离:
  user_id → sessions → memories → conversations
```

---

## 立即可落地的 4 项

### 1. 用户系统 (30 分钟)

```python
# 最小可用：微信 code → openid → JWT
/users/
├── login (POST)     # code → token
├── profile (GET)    # 用户信息
└── quota (GET)      # 剩余额度
```

### 2. 多租户隔离 (15 分钟)

```python
# 所有数据操作加上 user_id
memory.remember(content, user_id="wx_xxx")
session.create(user_id="wx_xxx")
```

### 3. 限流控制 (15 分钟)

```python
# Flask middleware: 每用户每分钟 10 次
@app.before_request
def rate_limit():
    user_id = get_user_id()
    if redis.get(f"rate:{user_id}") > 10:
        return {"error": "请求过于频繁"}, 429
```

### 4. 生产部署 (30 分钟)

```bash
gunicorn -w 4 -b 127.0.0.1:5000 agent.server:app
# Nginx 反代 + Let's Encrypt HTTPS
```

---

## 小程序上线 Checklist

```
[ ] 微信开放平台注册 (appid + secret)
[ ] 配置服务器域名 (request 合法域名)
[ ] 用户授权登录 (wx.login → code → openid)
[ ] 内容安全审核 (msgSecCheck)
[ ] 隐私协议页面
[ ] 提交审核
```

---

## 预算估算

| 项目 | 月费 |
|------|-----|
| 云服务器 (2C4G) | ¥100 |
| DeepSeek API | ¥200-500 |
| PostgreSQL (云数据库) | ¥50 |
| Redis | ¥30 |
| SSL 证书 | 免费 (Let's Encrypt) |
| CDN | 免费额度 |
| 微信认证费 | ¥300/年 |
| **合计** | **¥400-700/月** |

用户量 < 1000 以内，个人承担得起。
