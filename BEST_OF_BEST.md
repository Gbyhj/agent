# 优中取优：25 个项目最强基因融合

> 不是竞争，是学习。每个项目都有一件事做得比谁都好。
> 把这些"最好的一件事"拧在一起，就是别人抄不了的 Agent。

---

## 取优清单

| 来源 | 最强的单一能力 | 我们学了吗？ | 还缺什么？ |
|------|-------------|:--:|------|
| **Grok Build** | Session 生命周期管理 (Working→Idle→Dormant→Dead) | ❌ | 没有会话状态机 |
| **Smolagents** | Code-First 执行 (Agent 写 Python 不是 JSON) | ❌ | 没有 CodeAgent 模式 |
| **LangGraph** | StateGraph + Checkpointer 断点续传 | ❌ | 时间旅行有了，但缺 Reducer 语义合并 |
| **Mem0** | 向量+图谱混合检索 + 自动记忆提取 | ⚠️ | 有 VectorMemory 但缺 LLM 自动提取 |
| **Cline** | Plan/Act 双模式 + Checkpoint 追踪 | ⚠️ | Shell 有了但缺 Checkpoint diff 审查 |
| **OpenClaw** | Markdown 文件记忆 + HEARTBEAT 自主调度 | ❌ | 无心跳自主任务 |
| **Hermes Agent** | 自动技能生成 (任务→Skill 文件) | ❌ | 有条件反射但不会生成 .md 技能文件 |
| **LiteLLM** | Complexity Router (自动按难度选模型) | ⚠️ | 有关键词路由，缺真正的语义难度分析 |
| **Langfuse** | OpenTelemetry gen_ai.* 语义约定 | ❌ | 有 Tracer 但不用 OTEL 标准 |
| **E2B** | <200ms 冷启动隔离沙箱 | ❌ | 有 Docker 沙箱但没接入 E2B SDK |
| **CrewAI** | 角色-任务-团队声明式协作 | ⚠️ | 有元工厂但缺声明式编排语法 |
| **RAGAS** | 标准化评估指标 (答案相关性/事实一致性/检索精度) | ❌ | 有 Benchmark 但不用 RAGAS 指标 |
| **Browser-Use** | 视觉+DOM 双模态浏览器控制 | ❌ | 无浏览器工具 |
| **ChromaDB** | Python 原生向量数据库 (pip install 零依赖) | ✅ | 已有 |
| **Dify** | 可视化工作流编排 (拖拽式 RAG) | ❌ | 无可视化 |
| **n8n** | 400+ 原生集成节点 | ❌ | 无集成目录 |

---

## 核心缺失 — 最该学的那一个

看完 25 个项目源码，发现我们有 7 个创新但漏了 **三个最该学的东西**：

### 1. Grok Build 的 Session 状态机 🔴

```
我们:  Agent 启动 → 执行 → 结束（线性）
Grok:  Working → IdleResident(等待新消息) → Dormant(休眠)
       → Completed(归档) → DeadFailed(清理)

缺少:  会话可以暂停、休眠、恢复、跨天延续
```

### 2. Smolagents 的 CodeAgent 🔴

```
我们:  Agent 只支持 JSON tool_call
Smo:   Agent 可以直接写 Python 代码作为 Action
       单步调用 3 个工具 + 循环 + 条件判断
       省 30% LLM 调用

缺少:  CodeAgent 模式（Python 代码作为 action）
```

### 3. OpenClaw 的 HEARTBEAT 自主调度 🔴

```
我们:  用户不主动，Agent 就不动
OC:    心跳检查 → 发现未完成任务 → 自动执行
       定时任务 → Cron 调度 → 主动报告

缺少:  Agent 主动找活干的能力
```

---

## 今天补齐：三个最强基因

### 1. Session 状态机
```
idle → working → idle_resident → dormant → completed
  ↑        ↓            ↓
  └── resume ←── wake ──┘
```

### 2. CodeAgent 模式
```
Agent 可以选择:
  ToolCallingAgent: 传统 JSON tool_call
  CodeAgent:        直接写 Python → 沙箱执行
```

### 3. HEARTBEAT 自主调度
```
每 5 分钟检查:
  - 有未完成项目任务？→ 自动执行
  - 有定时任务到期？→ 执行
  - 有新消息？→ 处理
```

---

这三个基因补上后，Agent 就真正融合了最顶级的架构理念。
