# 25 个项目逐项拆解

> 2026-07-28 · 每个项目的唯一优势 + 我们取走了什么 + 还漏了什么

---

## 第一层：Agent 框架

### 1. Grok Build (⭐~) — 唯一优势: 四级沙箱 + 状态机
```
取走: SessionManager(6态生命周期) + SubAgentCoordinator + Goal验证
漏了: SandboxSystem的EventBus(所有沙箱操作走事件总线,可插拔审计)
  → 建议: sandbox/ 加 EventBus, 每个操作 publish event → 可观测/可回放
```

### 2. Smolagents (⭐14K) — 唯一优势: CodeAgent(LLM写代码代替JSON)
```
取走: CodeAgent + CodeInterpreter + 工具装饰器
漏了: code_agent的 persistent interpreter(变量跨轮次保持,重复利用)
  → 建议: CodeInterpreter加_persist标志,变量不销毁
```

### 3. OpenHands/CodeAct (⭐70K) — 唯一优势: 五步工程循环
```
取走: CodeActWorkflow(Explore→Analyze→Test→Implement→Verify)
漏了: Event Stream(每一步都是Event,可序列化→可回放→可分析)
  → 建议: agent loop 每步发出 Event, 存入 event_stream.jsonl
```

### 4. Cline (⭐20K) — 唯一优势: Diff Review + Checkpoint
```
取走: Plan/Act Shell + Provider抽象
漏了: Diff Preview(代码变更前先展示diff,用户确认后才写入)
  → 建议: WriteFileTool 加 preview_mode, 先返回diff
```

### 5. OpenClaw (⭐7K) — 唯一优势: 5000+ Skills 插件生态
```
取走: Heartbeat + Markdown文件记忆
漏了: Skills Registry(社区贡献的技能包,可搜索安装)
  → 建议: workflow_engine 加 skills 目录, 支持从文件加载自定义工作流
```

### 6. AutoGPT (⭐184K) — 唯一优势: Blocks可视化 + Marketplace
```
取走: 了解其架构(已被其他项目超越)
漏了: Blocks Builder(拖拽式构建Agent流水线,用户不写代码)
  → 远期目标,不是现在
```

### 7. Agno (⭐15K) — 唯一优势: 多模态Agent(文本+图像+音频统一)
```
取走: 无(研究不足)
漏了: MultimodalAgent(一次输入支持文本+图片+文件)
  → 建议: 为chat接口加files参数
```

---

## 第二层：工具 & Provider

### 8. LiteLLM (⭐20K) — 唯一优势: 100+ Provider · 智能成本路由
```
取走: SmartRouter(关键词匹配)
漏了: CostTracker(实时追踪费用,按model/project/user分组)
  → 建议: router加 cost_tracker,记录每次调用的token数和费用
```

### 9. Browser-Use (⭐94K) — 唯一优势: 视觉DOM双模态浏览器
```
取走: 无(未实现)
漏了: visual DOM extraction(截图+元素坐标+可交互元素列表)
  → 建议: 加 BrowserTool(based on Playwright)
```

### 10. Dify (⭐143K) — 唯一优势: 可视化RAG流水线
```
取走: WorkflowEngine(声明式YAML)
漏了: RAG Pipeline(文档上传→分段→embedding→检索,拖拽式)
  → 建议: 加 knowledge_base模块(kb_loader.py)
```

### 11. n8n (⭐188K) — 唯一优势: 400+原生集成
```
取走: 无
漏了: Connector Registry(标准化的输入输出端口)
  → 建议: tools/ 下加 connector抽象类(I/O port)
```

### 12. Qwen Code (⭐26K) — 唯一优势: 中文编码特化
```
取走: 无直接取用(用DeepSeek替代)
漏了: Code-specific的prompt模板(更适合中文代码场景)
  → 建议: AGENTS.md 加 中文编程提示词模板
```

---

## 第三层：协议 & 基础设施

### 13. MCP / ACP (Anthropic/Google) — 唯一优势: Agent间通信标准
```
取走: MCP Server/Client实现
漏了: A2A (Agent-to-Agent)协议(Google的Agent间协作新标准)
  → 建议: mcp/ 加 a2a_protocol.py
```

### 14. LangGraph (⭐20K) — 唯一优势: StateGraph可视化状态机
```
取走: State管理 + Processor概念
漏了: StateGraph可视化(把Agent的状态转换画成图)
  → 建议: SessionManager 加 to_mermaid()导出
```

### 15. Tree-sitter (⭐20K) — 唯一优势: 增量语法解析
```
取走: 无
漏了: AST-based代码分析(tools层用TST代替grep做精确代码搜索)
  → 建议: tools/ 加 ast_search.py
```

---

## 第四层：记忆 & 检索

### 16. Mem0 (⭐25K) — 唯一优势: 向量+图谱混合检索
```
取走: VectorMemory(ChromaDB)
漏了: Graph Memory(实体关系图谱: User→偏好→Python)
  → 建议: memory/graph_memory.py, 用networkx存实体关系
```

### 17. ChromaDB (⭐18K) — 唯一优势: Python原生零依赖
```
取走: 已集成
漏了: 无,很好
```

### 18. LlamaIndex (⭐42K) — 唯一优势: RAG全栈(加载→索引→查询→评估)
```
取走: 无
漏了: Document Loader(自动从项目文件生成向量索引)
  → 建议: tools/ 加 indexer.py, 自动为agent/目录建索引
```

---

## 第五层：评测 & 监控

### 19. RAGAS (⭐9K) — 唯一优势: 标准化评估指标
```
取走: Benchmark系统(5维度)
漏了: 答案相关性 + 事实一致性评估
  → 建议: benchmark.py加 relevance_score和 factual_accuracy
```

### 20. Langfuse (⭐12K) — 唯一优势: OTEL gen_ai语义约定
```
取走: AgentTracer
漏了: gen_ai.*语义标签(行业标准trace格式)
  → 建议: tracer.py加 gen_ai标签
```

---

## 第六层：平台

### 21. Everywhere (⭐6K) — 唯一优势: 屏幕感知(无需截图)
```
取走: 无
漏了: ScreenContext(获取当前活跃窗口/文件路径,注入上下文)
  → 建议: desktop_app加 active_file_detection
```

### 22. Claude Code / Codex CLI — 唯一优势: IDE深度集成
```
取走: 无(我们是独立Agent)
漏了: Terminal-native体验(ctrl+r搜索历史,tab补全)
  → 建议: shell.py加 readline支持
```

### 23. SST OpenCode — 唯一优势: 开箱即用的完整开发环境
```
取走: 无
漏了: DevContainer(docker一键启动开发环境)
  → 已有Docker,加 .devcontainer配置
```

---

## 机会清单

将 25 个项目尚未取走的优势按优先级排序:

### 🔴 高价值·低工作量(本周可做)

| # | 项目 | 漏了的能力 | 文件 | 工作量 |
|:--:|------|---------|------|:--:|
| 1 | Grok Build | Event Bus(可观测执行流) | `core/event_bus.py` | 30min |
| 2 | Cline | Diff Preview(写前确认) | tools内加preview | 20min |
| 3 | LiteLLM | Cost Tracker | `providers/cost_tracker.py` | 30min |
| 4 | Smolagents | Persistent Interpreter | CodeAgent改进 | 20min |
| 5 | OpenHands | Event Stream | `core/event_stream.py` | 30min |

### 🟡 中价值·中工作量

| # | 项目 | 漏了的能力 | 工作量 |
|:--:|------|---------|:--:|
| 6 | Mem0 | Graph Memory | 2h |
| 7 | Browser-Use | Browser Tool | 3h |
| 8 | OpenClaw | Skills Registry | 2h |
| 9 | Tree-sitter | AST-based Search | 2h |
| 10 | LlamaIndex | Auto Indexer | 1h |

### 🟢 长期

| # | 项目 | 漏了的能力 |
|:--:|------|---------|
| 11 | ACP/A2A | Agent间通信协议 |
| 12 | Dify | 可视化RAG Pipeline |
| 13 | AutoGPT | Blocks Builder |
| 14 | n8n | Connector Registry |

---

## 一句话总结

> 我们对 25 个项目的利用率约 **60%**。有 5 个高价值低工作量的能力可以本周补齐，直接推高 Agent 从 8.4 到 9.0+。
