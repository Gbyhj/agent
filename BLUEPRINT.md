# Agent 架构蓝图

> 基于 28 个开源 Agent 项目的深度分析，设计自己的 Agent 架构

## 设计哲学

| 来源 | 借鉴的理念 |
|------|-----------|
| **Grok Build** | Agent Loop (run_session), 工具注册 (NewTool trait), 权限门控, 沙箱分层 |
| **LangGraph** | StateGraph 有状态管理, Checkpointer 断点续传, Subgraph 组合 |
| **Smolagents** | Code-First 工具调用, 1000行核心极简哲学, 沙箱执行器抽象 |
| **OpenClaw** | Markdown 文件式记忆 (SOUL.md/MEMORY.md), 心跳自主调度 |
| **Hermes Agent** | 自动技能生成, 三层记忆, 自我进化闭环 |
| **Cline** | Plan/Act 双阶段, Provider 抽象层, 多端共享内核 |
| **CrewAI** | 角色-任务-团队声明式多 Agent 模型 |
| **Mem0** | 向量+图谱混合记忆, 即插即用 |
| **LiteLLM** | 100+ LLM 统一网关, 负载均衡+成本追踪 |
| **Langfuse** | OpenTelemetry 全链路 Trace, LLM-as-Judge 评估 |

## 架构分层

```
┌──────────────────────────────────────────────────────────┐
│                   Interface Layer                        │
│  CLI (交互) · HTTP API (SSE流式) · MCP Server            │
├──────────────────────────────────────────────────────────┤
│                   Agent Runtime                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Session   │  │ Context   │  │ LLM       │              │
│  │ Manager   │→ │ Builder   │→ │ Sampler   │              │
│  └──────────┘  └──────────┘  └─────┬────┘              │
│                                     │                    │
│  ┌──────────┐  ┌──────────┐  ┌─────▼────┐              │
│  │ Goal      │  │ Memory    │  │ Tool       │             │
│  │ System    │  │ System    │  │ Dispatcher │             │
│  └──────────┘  └──────────┘  └─────┬────┘              │
├────────────────────────────────────┼─────────────────────┤
│                   Tools Layer      │                     │
│  File (R/W/Search) · Shell (Sandbox) · Web (Browser)    │
│  SubAgent · MCP Bridge · Custom Plugins                  │
├──────────────────────────────────────────────────────────┤
│                 Infrastructure                           │
│  LiteLLM Gateway · ChromaDB · Mem0 · Langfuse · E2B     │
└──────────────────────────────────────────────────────────┘
```

## Agent Loop 详解

```
┌─────────────────────────────────────────────────────────┐
│  1. Context Builder                                     │
│     System Prompt + Memory Context + Tools Schema        │
│     + Conversation History + User Task                   │
├─────────────────────────────────────────────────────────┤
│  2. LLM Call                                            │
│     Model → Reasoning → Text + Tool Calls               │
│     (via LiteLLM for multi-model support)               │
├─────────────────────────────────────────────────────────┤
│  3. Tool Dispatch                                        │
│     Parse tool_calls → Permission Gate → Sandbox Exec    │
│     → Collect Observations                              │
├─────────────────────────────────────────────────────────┤
│  4. Loop Control                                         │
│     Final Answer? → Done                                 │
│     Tool Call Needed? → Back to Step 1                   │
│     Max Turns Reached? → Auto-stop                       │
│     Context > 85%? → Compact                             │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
agent/
├── core/
│   ├── agent.py          # Agent 主循环 (Agent class)
│   ├── tool_registry.py  # 工具注册中心 (ToolRegistry + @tool)
│   └── state.py          # 会话状态管理 (AgentState)
├── tools/
│   └── builtin.py        # 内置工具 (File/Shell/Search/Web)
├── memory/
│   └── memory.py         # 记忆系统 (Markdown文件式)
├── config/
│   └── default.toml      # 默认配置
├── providers/             # LLM Provider 适配器（未来）
├── sandbox/              # 沙箱执行环境（未来）
├── main.py               # CLI 入口
└── requirements.txt
```

## 技术选型

| 层 | 选型 | 原因 |
|----|------|------|
| 语言 | Python 3.11+ | 生态最丰富，Smolagents/LangGraph/Mem0 都是 Python |
| LLM 接入 | LiteLLM + OpenAI 兼容 | 一个接口调 100+ 模型 |
| 记忆 | Mem0 + Markdown 文件 | 语义检索 + 人类可读 |
| 向量存储 | ChromaDB | pip install 即用，LangChain 默认 |
| 可观测性 | Langfuse | OTEL 原生，Docker Compose 5分钟自托管 |
| 沙箱 | E2B / Docker | 冷启动<200ms |

## 开发路线

- [x] Phase 1: MVP 骨架
- [x] Phase 2: 7 Provider 统一接入
- [x] Phase 3: Plan/Act 双模式交互 CLI
- [x] Phase 4: SubAgent 并行子代理系统
- [ ] Phase 5: Langfuse 可观测性 Tracing
- [ ] Phase 6: Mem0 + ChromaDB 语义记忆
- [ ] Phase 7: MCP Server/Client
- [ ] Phase 8: Web UI
