# Agent v5 — 项目总览

> 两天，从零到 100 文件 · 16 项目基因 · 8 源码级改进 · 10 专家建议全绿

## 一句话

**3 秒审查代码安全的自主 AI Agent — 开源免费，三端可用**

## 核心亮点

| 类别 | 内容 |
|------|------|
| 🧬 基因融合 | 融合 Grok Build / Smolagents / OpenClaw / Mem0 / Cline / LangGraph / CrewAI / LiteLLM / Langfuse / E2B / RAGAS / ChromaDB / Browser-Use / Dify / Agno / AutoGPT |
| 💡 独创创新 | 渐进式工具解锁 · 会话驱动开发 · 条件反射系统 · 对抗式代码审查 · 成长型个人 AI · Agent 时间旅行 · 元 Agent 工厂 |
| 📐 源码改造 | Mem0实体图谱 · LiteLLM预检查链 · Dify VariablePool · Agno Fork分支 · LangGraph节点策略 · Browser-Use降级 · RAGAS逆问题评估 |
| 🏗️ 工程标准 | Google Design Doc · Code Review Checklist · SLOs · Feature Flags · AGENTS.md · GitHub Actions CI |
| 🧪 测试体系 | 冒烟(5) → 单元(3) → Beta(21) → 基准(A级95%) → Synthetic(10旅程100%) |
| 🎨 产品体验 | 免费体验 · 深色模式 · PWA · 语音输入 · 对话历史 · 分享 · 快捷键 |
| 📱 三端 | 桌面(PyWebView Win/Mac/Linux) · 网页(全浏览器) · 小程序(微信) |
| 📚 文档 | README · AGENTS.md · 设计文档 · 审计报告 · 25项目分析 · 源码拆解 |

## 架构

```
agent/
├── core/                    Agent 引擎 (18模块 · 3子包)
│   ├── engine/              Agent · State · CodeAct · CodeAgent · SubAgent
│   ├── infra/               Session · EventBus · VariablePool · NodeStrategy · FeatureFlags
│   └── features/            Reflex · Growth · TimeTravel · Adversarial · MetaFactory · Heartbeat
├── memory/                  记忆层 (3模块)
│   ├── memory.py            文件记忆
│   ├── vector_memory.py     ChromaDB向量
│   └── graph_memory.py      实体图谱 (Mem0公式)
├── tools/                   工具层 (4模块 · 7工具)
├── providers/               LLM层 (5模块)
│   ├── llm.py               7 Provider统一接口
│   ├── router.py            SmartRouter + Fallback链 + 镜像
│   ├── semantic_router.py   语义难度分析
│   ├── pre_call_checks.py   预检查链(健康/限流/预算/熔断)
│   └── mock.py              MockLLM测试工具
├── prompts/                 Prompt模板 (3模板 · 目录化管理)
├── sandbox/                 安全层
├── mcp/                     MCP协议
├── observability/           可观测 (Langfuse追踪)
├── tests/                   测试
├── apps/                    三端代码
│   ├── miniapp/             微信小程序
│   └── API.md               API规范
├── docs/                    工程文档
└── 15份专题文档              分析/审计/方案
```

## 测试成绩

```
Synthetic User Testing: ████████████████████ 10/10 (100%)
Beta Test:             ████████████████████ 21/21 (100%)
Benchmark:             ██████████████████░░ Grade A (95%)
9 Subsystems:          ████████████████████ All Green
```

## 专家评分

```
🏢 产品定位  ████████████████░░ 8.0  (+1.5)
🔒 安全      ███████████████░░░ 7.5
🏗️ 架构      ████████████████░░ 8.0
🤖 AI/LLM    ██████████████░░░░ 7.0
🎨 UX/体验   ██████████████░░░░ 7.0
⚡ 性能/SRE  ███████████████░░░ 7.5
🎯 设计/视觉  █████████████░░░░░ 6.5
────────────────────────────────
综合         ██████████████░░░░ 7.4
```

## 快速链接

| 地址 | 说明 |
|------|------|
| https://agent.保康.top | 项目首页 |
| https://agent.保康.top/agent | Web UI (免费体验) |
| https://agent.保康.top/kb | 知识库 (25项目) |
| https://github.com/Gbyhj/agent | GitHub 仓库 |
