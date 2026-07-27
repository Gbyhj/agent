# Agent 项目管理方案

> 2026-07-27 · 基于 25 个开源项目最佳实践

---

## 一、项目结构规范

```
agent/
├── core/                    # 核心引擎（不允许业务逻辑侵入）
│   ├── agent.py             # Agent Loop
│   ├── tool_registry.py     # 工具系统
│   ├── state.py             # 状态管理
│   ├── subagent.py          # 子代理
│   └── shell.py             # CLI Shell
├── tools/                   # 工具层（每个工具一个文件）
│   ├── builtin.py           # 6 核心工具
│   ├── web_search.py        # DuckDuckGo 搜索
│   ├── export.py            # 对话导出
│   └── templates.py         # 任务模板
├── memory/                  # 记忆层
│   ├── memory.py            # Markdown 文件记忆
│   └── vector_memory.py     # ChromaDB 语义记忆
├── providers/               # LLM 接入层
│   ├── llm.py               # 7 Provider 统一接口
│   └── router.py            # 智能路由
├── observability/           # 可观测性
│   └── tracer.py            # Langfuse 追踪
├── mcp/                     # 协议层
│   └── protocol.py          # MCP Server/Client
├── tests/                   # 测试（新增）
│   ├── test_core.py
│   ├── test_tools.py
│   └── test_memory.py
├── docs/                    # 文档（新增）
│   ├── ARCHITECTURE.md      # 架构文档
│   ├── API.md               # API 参考
│   └── CHANGELOG.md         # 变更日志
├── conversations/           # 对话导出目录（gitignore）
├── .agent_memory/           # Agent 记忆存储（gitignore）
├── main.py                  # CLI 入口
├── server.py                # Web API
├── test_agent.py            # 快速测试
├── start.bat                # Windows 启动
├── BLUEPRINT.md             # 架构蓝图
├── EXPERT_REVIEW.md         # 专家评审
├── requirements.txt         # 依赖
├── pyproject.toml           # 项目元数据（新增）
├── .gitignore               # Git 忽略规则（新增）
└── README.md                # 项目说明（新增）
```

### 模块边界规则

| 层 | 可以依赖 | 禁止依赖 |
|----|---------|---------|
| tools/ | core/ | memory/, providers/ |
| memory/ | core/ | tools/ |
| providers/ | 无 | core/, tools/ |
| core/ | providers/, memory/ | tools/（通过 ToolRegistry 注入） |
| observability/ | core/ | tools/, memory/ |

---

## 二、Git 仓库管理

### 初始化

```bash
cd agent/
git init
git checkout -b main

# .gitignore（已创建）
git add .
git commit -m "init: Agent v5 — 智能路由 + Planning + Goal验证 + 自修复"
```

### 分支策略

```
main          ← 稳定发布（只接受 PR 合入，禁止直接 push）
├── dev       ← 开发分支（日常开发）
│   ├── feature/xxx   ← 新功能
│   ├── fix/xxx       ← Bug 修复
│   └── refactor/xxx  ← 重构
└── release/v1.x  ← 发布候选
```

### Commit 规范

```
<type>(<scope>): <subject>

类型:
  feat     新功能
  fix      Bug修复
  refactor 重构
  docs     文档
  test     测试
  chore    工具/配置

范围:
  core, tools, memory, providers, mcp, obs

示例:
  feat(tools): add DuckDuckGo web search
  fix(core): auto-repair file path normalization
  refactor(memory): extract Mem0-style auto-memory
```

---

## 三、测试策略

### 测试金字塔

```
         /\
        /E2E\        集成测试: Agent 完整任务执行
       /------\
      / 集成   \      单元测试: 工具/记忆/Provider 独立测试
     /----------\
    /   单元     \    冒烟测试: 导入验证、基础功能
   /--------------\
```

### 测试文件组织

```python
tests/
├── test_core/
│   ├── test_agent.py       # Agent Loop 测试
│   ├── test_tool_registry.py  # 工具注册测试
│   └── test_state.py       # 状态管理测试
├── test_tools/
│   ├── test_builtin.py     # 6 内置工具测试
│   └── test_web_search.py  # 搜索工具测试
├── test_memory/
│   ├── test_memory.py      # 文件记忆测试
│   └── test_vector.py      # 向量记忆测试
└── test_integration/
    └── test_agent_run.py   # 端到端测试
```

### 测试命令

```bash
# 全部测试
python -m pytest tests/ -v

# 快速冒烟
python agent/main.py --test

# 单模块
python -m pytest tests/test_core/ -v

# 覆盖率
python -m pytest tests/ --cov=agent --cov-report=html
```

---

## 四、CI/CD 流水线

### GitHub Actions

```yaml
name: Agent CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: python -m pytest tests/ -v --cov=agent

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check agent/

  deploy-kb:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Cloudflare Pages
        run: |
          npm install -g wrangler
          cd kb
          wrangler pages deploy . --project-name=agent-kb --branch=main
        env:
          CLOUDFLARE_API_KEY: ${{ secrets.CF_KEY }}
          CLOUDFLARE_EMAIL: ${{ secrets.CF_EMAIL }}
```

---

## 五、版本发布流程

### 语义化版本

```
v1.0.0  → 首个稳定版
v1.1.0  → 新功能（后向兼容）
v1.1.1  → Bug 修复
v2.0.0  → 破坏性变更
```

### 发布 Checklist

```
[ ] 全部测试通过
[ ] CHANGELOG.md 更新
[ ] 文档更新
[ ] Git tag: git tag -a v1.0.0 -m "Release v1.0.0"
[ ] 推送: git push --follow-tags
[ ] 知识库同步: wrangler pages deploy
[ ] 发布公告（agent.保康.top 更新）
```

---

## 六、知识库同步

### 自动同步策略

```
源码更新 → 提取摘要 → 更新 data.js → wrangler deploy
                                      ↓
                              agent.保康.top 上线
```

### 同步脚本

```bash
#!/bin/bash
# sync_kb.sh — 同步项目变更到知识库

echo "提取项目摘要..."
python -c "
from agent.core.agent import Agent, AgentConfig
# 自动生成项目摘要
" > /tmp/kb_update.json

echo "部署到 agent.保康.top..."
cd kb
wrangler pages deploy . --project-name=agent-kb --branch=main
```

---

## 七、开发路线图

### 当前版本: v5 — 智能 Agent
```
✅ Agent Loop        ✅ 工具系统        ✅ 7 Provider
✅ 智能路由          ✅ 免费搜索        ✅ Planning
✅ Goal 验证         ✅ 自修复          ✅ 自动记忆
✅ SubAgent          ✅ MCP             ✅ Langfuse
✅ Web UI            ✅ 对话导出        ✅ 8 任务模板
✅ start.bat
```

### 下一版本: v6 — 企业级

| 功能 | 优先级 | 工作量 |
|------|:--:|:--:|
| Docker Compose 部署 | P0 | 2h |
| 消息平台接入 (Telegram) | P0 | 3h |
| LLM 流式输出 (SSE) | P1 | 2h |
| 配置文件系统 (config.toml) | P1 | 1h |
| Playwright 浏览器工具 | P2 | 3h |
| Context Window 优化 | P2 | 2h |
| 多语言支持 (en) | P3 | 2h |

### 远期目标: v7 — 平台化

```
- MCP Server 让外部 AI 调用你的 Agent
- 插件市场 (Plugin Registry)
- A2A 协议 (Agent-to-Agent)
- 分布式 SubAgent
```

---

## 八、日常维护

### 每周

```bash
# 更新依赖
pip install --upgrade -r requirements.txt

# 运行全量测试
python -m pytest tests/ -v

# 查看记忆增长
python -c "from agent.memory.vector_memory import VectorMemory; print(VectorMemory().stats())"

# 清理旧对话
find conversations/ -mtime +30 -delete
```

### 每月

```bash
# 代码审查
python -m agent.main --template code-review --target agent/

# 知识库更新
cd kb && wrangler pages deploy .
```

---

## 九、安全规范

```
[ ] API Key 不进 Git（.env 或环境变量）
[ ] 每次发布前审查工具权限
[ ] 第三方依赖审计: pip audit
[ ] 敏感路径保护: ~/.ssh, ~/.aws 过滤
[ ] 命令白名单优先于黑名单
```
