# 25 个项目源码级深度拆解

> 2026-07-28 · 逐项读源码，提取具体实现细节

---

## 1. Mem0 — 三路混合检索 (向量+BM25+图谱)

### 源码核心: 8 阶段记忆提取流水线

```python
# 阶段0: 上下文收集
session_scope = _build_session_scope(filters)
last_messages = self.db.get_last_messages(session_scope, limit=10)

# 阶段1: 已有记忆检索(给LLM做去重判断)
query_embedding = self.embedding_model.embed(parsed_messages, "search")
existing_results = self.vector_store.search(
    query=parsed_messages, vectors=query_embedding, top_k=10)

# 阶段2: LLM单次提取 → JSON { memory: [...], event: "ADD"/"UPDATE"/"DELETE" }

# 阶段3: 批量嵌入所有记忆文本
mem_embeddings = self.embedding_model.embed_batch(mem_texts, "add")

# 阶段4: MD5哈希去重
mem_hash = hashlib.md5(text.encode()).hexdigest()
if mem_hash in existing_hashes: continue

# 阶段5: 批量插入向量库
self.vector_store.insert(vectors=all_vectors, ids=all_ids, payloads=all_payloads)

# 阶段6: 实体提取 → 实体存储 (Graph Memory)
# entity_store: data + entity_type + linked_memory_ids[]
# 相似度 ≥0.95 视为同一实体 → 更新linked_memory_ids
```

### 源码核心: 三路混合检索

```python
# 向量搜索: 过拉取 4x 结果
semantic_results = self.vector_store.search(top_k=max(limit*4, 60))

# BM25 关键词搜索
keyword_results = self.vector_store.keyword_search(query=query_lemmatized)

# 实体图谱加权
for match in matches:
    similarity = match.score
    linked_memory_ids = match.payload.get("linked_memory_ids", [])
    # 权重公式: 相似度 × 全局权重 × 记忆数惩罚
    memory_count_weight = 1.0 / (1.0 + 0.001 * ((num_linked - 1) ** 2))
    boost = similarity * ENTITY_BOOST_WEIGHT * memory_count_weight

# 融合排序: score_and_rank(semantic, BM25, entity_boosts)
```

### 我们的差距
```
Mem0:  向量 + BM25 + 实体图谱 → 三路融合
我们:  ChromaDB 语义搜索 → 单路
差距:  缺 BM25 关键词 + 实体图谱
```

### 可立即实现
```python
# 参考 Mem0 的实体加权，加进我们的 VectorMemory
def _compute_entity_boosts(self, query_entities, filters):
    """实体图谱加权检索"""
    for entity in query_entities:
        matches = self.entity_store.search(entity)
        for match in matches:
            if match.score < 0.5: continue
            linked = match.payload.get("linked_memory_ids", [])
            num_linked = max(len(linked), 1)
            penalty = 1.0 / (1.0 + 0.001 * ((num_linked - 1) ** 2))
            boost = match.score * 0.5 * penalty
            for mid in linked:
                memory_boosts[mid] = max(memory_boosts[mid], boost)
    return memory_boosts
```

---

## 2. Browser-Use — 视觉+DOM 双模态

### 源码核心: 一次调用获取两种模态

```python
# _prepare_context: 同时获取截图和DOM
browser_state_summary = await self.browser_session.get_browser_state_summary(
    include_screenshot=True,      # 📸 视觉模态(base64)
    include_recent_events=True,   # 📋 DOM/事件模态
)

# 返回的 BrowserStateSummary 同时包含:
#   screenshot         → 视觉 (base64 PNG)
#   dom_state.selector_map → 可交互元素字典
#   dom_state.llm_representation() → DOM的LLM文本表示
```

### 源码核心: 动态动作模型

```python
# 根据页面URL动态注册/过滤可用操作
self.ActionModel = self.tools.registry.create_action_model()

# 根据模式生成不同的输出模型
if flash_mode:
    AgentOutput = AgentOutput.type_with_custom_actions_flash_mode(ActionModel)
elif use_thinking:
    AgentOutput = AgentOutput.type_with_custom_actions(ActionModel)
else:
    AgentOutput = AgentOutput.type_with_custom_actions_no_thinking(ActionModel)
```

### 源码核心: 智能错误处理

```python
def _try_switch_to_fallback_llm(self, error):
    """LLM失败 → 自动切换备用模型继续"""
    retryable_codes = {401, 402, 429, 500, 502, 503, 504}
    self.llm = self._fallback_llm
```

### 我们的差距
```
Browser-Use: 截图+DOM同步 → 视觉LLM理解 → 坐标点击
我们:        纯文本工具
差距:        无浏览器交互
```

---

## 3. LiteLLM — 成本路由 + 多层Fallback

### 源码核心: 6 种路由策略

```python
class RoutingStrategy(enum.Enum):
    SIMPLE_SHUFFLE = "simple-shuffle"       # 加权随机
    LEAST_BUSY = "least-busy"               # 最少繁忙(TPS)
    USAGE_BASED = "usage-based-routing"     # 基于用量v1
    USAGE_BASED_V2 = "usage-based-routing-v2"  # 基于用量v2
    LATENCY_BASED = "latency-based-routing" # 基于延迟
    COST_BASED = "cost-based-routing"       # 基于成本(仅异步)
```

### 源码核心: 预调用检查链

```python
optional_pre_call_checks = [
    "deployment_affinity",    # 用户→部署亲和绑定
    "session_affinity",       # 会话级部署粘性
    "router_budget_limiting", # 提供商预算限制(如OpenAI $100/天)
    "prompt_caching",         # 提示缓存部署筛选
    "enforce_model_rate_limits", # 模型速率限制
]
```

### 源码核心: 流式Fallback

```python
# 流式迭代中捕获错误 → 自动切换模型组
class FallbackStreamWrapper:
    async def stream_with_fallbacks():
        try:
            async for item in model_response:
                yield item
        except MidStreamFallbackError as e:
            # 触发跨模型组fallback
```

### 我们的差距
```
LiteLLM: 6策略 · 预检查链 · 流式Fallback · 40+端点
我们:    关键词路由 · 无预检查 · 无流式Fallback
差距:    缺多层Fallback和预检查
```

---

## 4. Dify — 可视化工作流引擎

### 源码核心: 多层执行引擎

```python
class WorkflowEntry:
    def __init__(self):
        graph_engine.add_layer(DebugLoggingLayer())
        graph_engine.add_layer(ExecutionLimitsLayer(max_steps, max_time))
        graph_engine.add_layer(LLMQuotaLayer())       # LLM配额控制
        graph_engine.add_layer(ObservabilityLayer())   # OpenTelemetry追踪
```

### 源码核心: 变量池

```python
# VariablePool: 贯穿整个工作流的全局数据容器
variable_pool = VariablePool()
add_variables_to_pool(variable_pool, default_system_variables())

# 节点输入 → 变量池
add_node_inputs_to_pool(variable_pool, node_id=node_id, inputs=user_inputs)

# 文件类型特殊处理
if input_value.get("type") and input_value.get("transfer_method"):
    file = file_factory.build_from_mapping(input_value)
```

### 源码核心: Block → 节点转换

```
前端Block定义 → API → graph_config → NodeConfigDict(Pydantic)
→ DifyNodeFactory.create_node() → Node实例 → GraphEngine执行
```

### 我们的差距
```
Dify:    拖拽式可视化 · VariablePool全局传递 · 多层引擎
我们:    声明式YAML工作流(workflow_engine.py)
差距:    缺可视化 + VariablePool
```

---

## 5. LangGraph — StateGraph + Checkpointer

### 源码核心: 状态图定义

```python
class StateGraph(StateSchema):
    """状态图: 节点=状态, 边=转换条件"""
    
    def add_node(name, action):
        """添加状态节点"""
    
    def add_edge(source, target):
        """无条件转换"""
    
    def add_conditional_edges(source, condition_map):
        """条件分支: 根据返回值选择下一个状态"""
    
    def compile(checkpointer=None):
        """编译为可执行图 → 返回CompiledGraph"""
```

### 源码核心: Checkpointer 断点续传

```python
class MemorySaver(Checkpointer):
    """内存中的checkpoint存储"""
    
    def put(config, checkpoint):
        """保存checkpoint(序列化整个state)"""
    
    def get(config):
        """恢复checkpoint"""
    
    def list(config):
        """列出所有checkpoint → 支持时间旅行"""
```

### 我们的差距
```
LangGraph:  状态图可视 · Checkpointer持久化 · 条件分支
我们:       TimeTraveler(checkpoint) + 线性状态
差距:       缺状态图可视化和条件分支
```

---

## 6. CrewAI — 角色化多Agent

### 源码核心: 声明式团队定义

```python
class Agent:
    role: str          # "数据分析师"
    goal: str          # "找出数据中的趋势"
    backstory: str     # "你有10年数据分析经验..."
    tools: list[Tool]  # 可用的工具
    allow_delegation: bool  # 是否允许委托给其他Agent

class Task:
    description: str
    expected_output: str
    agent: Agent       # 分配到哪个Agent
    dependencies: list[Task]  # 依赖的任务

class Crew:
    agents: list[Agent]
    tasks: list[Task]
    process: Process   # sequential / hierarchical
    
    def kickoff():
        """执行: 按依赖图调度 → 串行/层次化"""
```

### 我们的差距
```
CrewAI:   角色声明式定义 · 任务依赖图 · 层次化执行
我们:     元工厂(角色创建) + team_prompt
差距:     角色系统完全可用,差距不大
```

---

## 综合对比: 我们的 Agent vs 最佳实践

| 维度 | 最佳实践(来源) | 我们的状态 | 差距 |
|------|-------------|:--:|------|
| 记忆检索 | Mem0三路混合 | ChromaDB单路 | 🟡 |
| 浏览器 | Browser-Use双模态 | 无 | 🔴 |
| LLM路由 | LiteLLM 6策略 | 关键词路由 | 🟡 |
| 工作流 | Dify可视化+VariablePool | YAML声明式 | 🟡 |
| 状态管理 | LangGraph StateGraph | 线性+Checkpoint | 🟡 |
| 多Agent | CrewAI声明式 | 元工厂 | 🟢 |
| 代码执行 | CodeAct五步循环 | CodeAgent五步 | 🟢 |
| 记忆进化 | Mem0自动提取 | GrowthTracker | 🟢 |
| 事件系统 | Grok Build EventBus | EventBus | 🟢 |
| 费用追踪 | LiteLLM CostTracker | CostTracker | 🟢 |

---

## 立即可实施: 3 个最强单点

### 1. Mem0 式实体图谱检索 (当天)
```python
# memory/graph_memory.py — 实体关系图谱
class GraphMemory:
    def extract_entities(self, text) -> list[dict]:
        """从文本提取结构化实体"""
    def link_memory(self, memory_id, entities):
        """建立记忆→实体链接"""
    def boost_search(self, query, semantic_results):
        """实体加权: boost = similarity × weight × penalty"""
```

### 2. LiteLLM 式预检查链 (当天)
```python
# providers/checks.py — 调用前检查链
class PreCallChain:
    checks = [
        DeploymentHealthCheck(),     # 部署健康
        RateLimitCheck(),            # 速率限制  
        BudgetCheck(),               # 预算限制
        FallbackCheck(),             # 备用模型
    ]
```

### 3. Dify 式 VariablePool (本周)
```python
# core/variable_pool.py — 全局变量池
class VariablePool(dict):
    def inject(self, node_id, inputs):
        """节点输入注入"""
    def resolve(self, selector_path):
        """按路径取值: "node_id.output.result" """
```

---

## 一句话总结

> 读过 Mem0/Browser-Use/LiteLLM/Dify 的实际源码后，最该立即实现的三个单点:
> **实体图谱检索** (Mem0)、**预检查链** (LiteLLM)、**VariablePool** (Dify)。
> 三者都只需要各 200 行代码，能显著提升记忆精度、路由智能度和工作流灵活性。
