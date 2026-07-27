# 专家团评审：你的 Agent 定制方案

> 评审日期：2026-07-27
> 评审依据：25 个项目源码分析 + Smolagents/Mem0/Cline/Grok Build 源码级深挖 + 设计模式参考

---

## 专家团成员

| 专家 | 专长 | 关注点 |
|------|------|--------|
| **E1 架构师** | Agent 系统设计 | 整体架构、模块边界、数据流 |
| **E2 LLM 工程师** | 模型接入与优化 | Provider 选择、成本控制、中文支持 |
| **E3 记忆系统专家** | 持久化与检索 | 记忆架构、混合检索、知识积累 |
| **E4 安全专家** | 沙箱与权限 | 代码执行安全、命令过滤、权限模型 |
| **E5 工具系统专家** | 工具设计与扩展 | 工具注册、MCP 集成、插件机制 |
| **E6 DevOps 工程师** | 部署与运维 | Windows 部署、可观测性、持续运行 |

---

## E1 架构师 · 整体方案

### 现状评估

你的 `agent/` 项目已有坚实的基础：
- Agent Loop ✅（融合 Grok Build + Smolagents）
- 工具系统 ✅（BaseTool + @tool + ToolRegistry）
- 7 Provider ✅（LLM 层抽象）
- 记忆系统 ✅（文件 + ChromaDB 语义）
- Plan/Act CLI ✅
- MCP 协议 ✅

### 架构建议：三层精简

```
┌─────────────────────────────────────────────┐
│              Interface Layer                │
│   CLI (Plan/Act Shell)  ·  Web UI (Flask)   │
│   MCP Server (让外部 AI 调用你的 Agent)      │
├─────────────────────────────────────────────┤
│              Agent Runtime                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ Session  │  │ Context   │  │ LLM        │ │
│  │ Manager  │→ │ Builder   │→ │ Dispatcher │ │
│  └──────────┘  └──────────┘  └─────┬─────┘ │
│                                     │       │
│  ┌──────────┐  ┌──────────┐  ┌─────▼─────┐ │
│  │ Memory   │  │ Tool      │  │ Permission │ │
│  │ System   │  │ Registry  │  │ Gate       │ │
│  └──────────┘  └──────────┘  └───────────┘ │
├─────────────────────────────────────────────┤
│              Infrastructure                 │
│  LiteLLM Gateway  ·  ChromaDB  ·  Langfuse  │
│  Docker Sandbox   ·  Cron Scheduler         │
└─────────────────────────────────────────────┘
```

### 关键决策

| 决策点 | 选型 | 理由 |
|--------|------|------|
| 语言 | Python 3.11+ | 生态最全，你已熟悉的栈 |
| 主模型 | DeepSeek V4 | 中文最优，性价比高 |
| 备用模型 | SiliconFlow (Qwen) | 国产替代，免费用额度 |
| 本地模型 | Ollama (Qwen3-Coder) | 离线/隐私场景 |
| Agent 模式 | ReAct + 可选 Code-First | Smolagents 的双 Agent 设计 |
| 状态管理 | AgentState dataclass | 你已有，够用 |
| 记忆方案 | Mem0 优先，文件兜底 | 向量+图谱混合，21+ 集成 |
| 部署方式 | Python 进程 + systemd | 简单可靠 |

### ⚠️ 不要做的事

- **不要引入 LangChain** — 你的 500 行 Agent Loop 已经够好，LangChain 的抽象层只会增加复杂度
- **不要过早分布式** — 单个 Agent 进程 + SubAgent 线程池完全够用
- **不要复杂配置文件** — 环境变量 + 一个 config.toml 足矣

---

## E2 LLM 工程师 · 模型方案

### 推荐模型矩阵

| 场景 | 模型 | Provider | 成本 | 延迟 |
|------|------|----------|------|------|
| 复杂推理 | DeepSeek V4 Pro | deepseek | ¥2/M tokens | ~2s |
| 日常任务 | DeepSeek V4 Flash | deepseek | ¥0.5/M tokens | ~0.5s |
| 代码生成 | Qwen3-Coder-480B | siliconflow | 免费额度 | ~1s |
| 离线模式 | Qwen3-Next-80B (3B active) | Ollama 本地 | 0 | ~20 tok/s |
| 中文理解 | GLM-5 | zhipu | ¥1/M tokens | ~1.5s |

### 自动路由策略（参考 LiteLLM Complexity Router）

```python
COMPLEXITY_ROUTER = {
    "simple": {   # 读取文件、列出目录
        "model": "deepseek-v4-flash",
        "max_tokens": 2048,
    },
    "medium": {   # 代码搜索、分析
        "model": "deepseek-v4-flash",
        "max_tokens": 4096,
    },
    "complex": {  # 重构、多文件修改
        "model": "deepseek-v4-pro",
        "max_tokens": 8192,
    },
    "code_gen": { # 写代码
        "model": "qwen3-coder-plus",
        "provider": "siliconflow",
    },
}

def route_model(task: str) -> dict:
    if any(kw in task for kw in ["重构", "架构", "设计"]):
        return COMPLEXITY_ROUTER["complex"]
    if any(kw in task for kw in ["写", "实现", "创建"]):
        return COMPLEXITY_ROUTER["code_gen"]
    if len(task) < 50:
        return COMPLEXITY_ROUTER["simple"]
    return COMPLEXITY_ROUTER["medium"]
```

### 成本控制

- 设置每日预算上限（如 ¥5/天）
- 优先用 SiliconFlow 免费额度
- 离线时自动切换 Ollama 本地模型
- 上下文 > 85% 自动压缩（你已有）

---

## E3 记忆系统专家 · 记忆方案

### 三层记忆架构

```
Layer 1: 工作记忆（AgentState.messages）
  └─ 当前会话上下文，最近 20 条消息
  └─ 会话结束 → 择要写入 L2

Layer 2: 语义记忆（Mem0 + ChromaDB）
  └─ 向量+图谱混合存储
  └─ 自动从对话提取关键事实
  └─ 支持语义检索

Layer 3: 文件记忆（Markdown）
  └─ SOUL.md: Agent 人格
  └─ MEMORY.md: 核心偏好
  └─ daily/*.md: 每日日志
  └─ projects/*.md: 项目知识
```

### 记忆生命周期

```
用户对话 → Mem0.add(messages)
  ├─ LLM 提取关键事实
  ├─ 向量化 + MD5 去重
  ├─ 存储到 ChromaDB
  └─ 实体链接到知识图谱

Agent 推理前 → Mem0.search(query)
  ├─ 语义搜索 (top_k*4)
  ├─ BM25 关键词搜索
  ├─ 实体图谱增强
  └─ 注入 LLM 上下文
```

### ⚠️ 记忆清理策略

- 工作记忆：会话结束自动清理
- 语义记忆：90 天未访问 → 降权；180 天 → 归档
- 文件记忆：永久保留（git 版本化）

---

## E4 安全专家 · 安全方案

### 四级权限模型（参考 Grok Build + Cline）

```
Level 0: Trusted（默认）
  ├─ 读取任何文件
  ├─ 写入工作目录
  ├─ 执行只读命令（ls, cat, grep, git log）
  └─ 访问外网（搜索、API）

Level 1: Sandboxed（代码执行）
  ├─ Docker 容器隔离
  ├─ 只读根文件系统
  ├─ 网络隔离
  └─ 内存/CPU 限制

Level 2: Restricted（敏感操作）
  ├─ 需人工确认
  ├─ 30 分钟自动过期
  └─ 审计日志记录

Level 3: Blocked（永久禁止）
  ├─ rm -rf /
  ├─ 修改系统文件
  ├─ 访问 ~/.ssh、~/.aws
  └─ 网络端口扫描
```

### 命令安全过滤（你已有，需增强）

```python
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"sudo\s+",
    r"chmod\s+777",
    r">\s*/dev/",
    r"mkfs\.",
    r"dd\s+if=",
    r"curl.*\|\s*bash",    # 管道执行
    r"wget.*-O\s*-\s*\|\s*sh",
]

SENSITIVE_PATHS = [
    "~/.ssh", "~/.aws", "~/.gcloud",
    "/etc/passwd", "/etc/shadow",
    "~/.bash_history", "~/.zsh_history",
]
```

---

## E5 工具系统专家 · 工具方案

### 核心工具集（6 个已有 + 4 个新增）

| 工具 | 来源 | 优先级 |
|------|------|:--:|
| read_file | 已有 | P0 |
| write_file | 已有 | P0 |
| list_dir | 已有 | P0 |
| grep | 已有 | P0 |
| bash | 已有 | P0 |
| web_fetch | 已有 | P0 |
| **web_search** (Tavily/SerpAPI) | 新增 | P1 |
| **browser** (Playwright) | 新增 | P1 |
| **task** (SubAgent) | 已有 subagent.py | P1 |
| **mcp_bridge** | 已有 mcp/protocol.py | P2 |

### 工具注册规范

```python
# 每个工具 = 一个文件
tools/
├── builtin.py        # 已有 6 个
├── web_search.py     # 新增
├── browser.py        # 新增
├── mcp_bridge.py     # 已有 protocol.py，包装为工具
└── __init__.py
```

---

## E6 DevOps 工程师 · 部署方案

### 推荐 Windows 部署

```powershell
# 1. 克隆项目
git clone <your-repo> agent
cd agent

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置
set DEEPSEEK_API_KEY=sk-xxx
set AGENT_PROVIDER=deepseek

# 5. 启动
python server.py        # Web UI
python -m agent.main    # CLI
```

### 后台运行（Windows）

```powershell
# 注册为 Windows 服务
# 或使用 start- agent .bat 脚本
```

### 可观测性（可选）

```bash
# 启动 Langfuse（Docker Compose 5 分钟）
git clone https://github.com/langfuse/langfuse.git
cd langfuse && docker compose up -d

# Agent 配置中开启
export LANGFUSE_PUBLIC_KEY=pk-xxx
export LANGFUSE_SECRET_KEY=sk-xxx
```

---

## 整合方案：你的 Agent v5

### 最终架构

```python
# 你的 Agent 启动流程
agent = Agent(
    # 模型层
    llm=AutoRouter([
        DeepSeekV4(flash=True),     # 日常任务
        DeepSeekV4(flash=False),    # 复杂推理
        Qwen3Coder(),               # 代码生成
        Ollama("qwen3-coder"),      # 离线
    ]),

    # 记忆层
    memory=HybridMemory(
        working=ConversationBuffer(k=20),
        semantic=Mem0(collection="my-agent"),
        files=MarkdownMemory("./.agent_memory"),
    ),

    # 工具层
    tools=[ReadFile(), WriteFile(), Grep(), Bash(), WebSearch(), Browser(), Task()],

    # 安全层
    sandbox=Sandbox(level="workspace", docker=True),
    permission=PermissionGate(allow_unsafe=False),

    # 观测层
    tracer=LangfuseTracer(enabled=True),
)
```

### 与现有 agent/ 项目的关系

```
你的 agent/ 项目已完成 7/8 阶段：
✅ Agent Loop      → 直接用
✅ 工具系统         → 直接用
✅ 7 Provider      → 直接用，加 AutoRouter
✅ 状态管理         → 直接用
✅ 记忆系统         → 替换为 Mem0（已有 ChromaDB 层）
✅ Plan/Act CLI    → 直接用
✅ MCP 协议         → 直接用
⬜ 部署脚本          → 本次新增
```

### 下一步（按优先级）

| 优先级 | 任务 | 预计工作量 |
|:--:|------|:--:|
| P0 | 集成 Mem0 替换文件记忆 | 2 小时 |
| P0 | 添加 AutoRouter 模型自动路由 | 1 小时 |
| P0 | Windows 部署脚本 (start.bat) | 30 分钟 |
| P1 | 添加 Web Search 工具 (Tavily/SerpAPI) | 1 小时 |
| P1 | 配置文件系统 (config.toml) | 1 小时 |
| P2 | Docker 沙箱安全执行 | 2 小时 |
| P2 | Langfuse 可观测性 | 1 小时 |
| P3 | 消息平台接入 (Telegram/微信) | 3 小时 |

---

## 评审结论

> **你的 agent/ 项目架构已经非常扎实。** 当前最缺的不是新功能，而是三个关键集成：Mem0 语义记忆（让 Agent 真正「记住」）、AutoRouter（多模型智能切换）、以及 Windows 部署脚本。这三项完成后，就是一个可日常使用的个人 AI Agent 了。
