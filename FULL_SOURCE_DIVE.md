# 25 项目源码级完整拆解

> 2026-07-28 · 实际读取 7 个项目源码 · 提取具体实现

---

## 1. Mem0 → 8 阶段记忆流水线 + 三路融合检索

### 源码: add() 的 8 阶段批处理

```
阶段0: 收集上下文 (build_session_scope + 最近10条消息)
阶段1: 检索已有记忆 (embed → vector_store.search top-10)
阶段2: LLM单次提取 (ADDITIVE_EXTRACTION_PROMPT → JSON)
阶段3: 批量嵌入 (embed_batch → 失败则逐条)
阶段4: MD5哈希去重 (跳过重复+当前批次内重复)
阶段5: 批量插入向量库 (先批量,失败则回退逐条)
阶段6: 实体提取 (extract_entities_batch → entity_store)
阶段7: 实体链接 (相似度≥0.95视为同实体 → 更新linked_memory_ids)
阶段8: 保存消息 + 返回
```

### 源码: search() 三路融合公式
```python
# 1. 语义向量搜索 (过拉取4x,最少60条)
semantic_results = vector_store.search(top_k=max(limit*4, 60))

# 2. BM25关键词 (词形还原 + S型归一化)
bm25_scores = normalize_bm25(raw_score, midpoint, steepness)

# 3. 实体图谱加权 (含惩罚因子)
boost = similarity * 0.5 * 1/(1 + 0.001 * (num_linked-1)²)

# 融合: score_and_rank(semantic, bm25, entity_boosts)
```

**可取**: 实体惩罚因子公式直接可用

---

## 2. Browser-Use → 双模态同步 + 动态动作模型

### 源码: 一次调用获取两种模态
```python
browser_state_summary = await browser_session.get_browser_state_summary(
    include_screenshot=True,    # 📸 base64 PNG
    include_recent_events=True, # 📋 DOM结构
)
# 返回: .screenshot(视觉) + .dom_state.selector_map(可交互元素)
#      + .dom_state.llm_representation()(LLM可读文本)
```

### 源码: 消息管线
```python
_message_manager.create_state_messages(
    browser_state_summary=browser_state_summary,  # 截图+DOM
    model_output=last_output,                     # 上一步输出
    use_vision=settings.use_vision,               # 是否发截图给LLM
)
```

### 源码: 智能降级
```python
def _try_switch_to_fallback_llm(self, error):
    retryable_codes = {401, 402, 429, 500, 502, 503, 504}
    self.llm = self._fallback_llm  # 自动切换备用模型
```

### 源码: 坐标点击支持
```python
# 特定模型自动启用坐标点击
supports_coordinate_clicking = any(
    pattern in model_name
    for pattern in ['claude-sonnet-4', 'gemini-3-pro', 'browser-use/']
)
```

**可取**: 消息管线化 · 智能降级策略 · 坐标点击模型检测

---

## 3. LiteLLM → 6 策略路由 + 预检查链

### 源码: 6 种路由策略枚举
```python
SIMPLE_SHUFFLE      # 加权随机
LEAST_BUSY          # 最少繁忙(TPS)
USAGE_BASED         # 基于用量v1  
USAGE_BASED_V2      # 基于用量v2
LATENCY_BASED       # 基于延迟
COST_BASED          # 基于成本(仅异步)
```

### 源码: 预调用检查链
```python
optional_pre_call_checks = [
    "deployment_affinity",         # 用户→部署亲和绑定
    "session_affinity",            # 会话级部署粘性
    "router_budget_limiting",      # 提供商预算($100/天)
    "prompt_caching",              # 提示缓存筛选
    "enforce_model_rate_limits",   # 速率限制
]
```

### 源码: 流式 Fallback 包装器
```python
class FallbackStreamWrapper:
    async def stream_with_fallbacks():
        try:
            async for item in model_response:
                yield item
        except MidStreamFallbackError:
            # 跨模型组 fallback
```

### 源码: Silent Model 流量镜像
```python
silent_model = litellm_params.pop("silent_model", None)
if silent_model:
    thread = Thread(target=self._silent_experiment_completion, ...)
    thread.start()  # A/B测试: 后台线程跑另一个模型,不影响主链路
```

**可取**: 预检查链 · 流式Fallback · 静默流量镜像

---

## 4. Dify → VariablePool + 多层引擎

### 源码: 引擎层叠
```python
graph_engine.add_layer(DebugLoggingLayer())       # 调试日志
graph_engine.add_layer(ExecutionLimitsLayer())    # 步数/时间限制
graph_engine.add_layer(LLMQuotaLayer())           # LLM配额
graph_engine.add_layer(ObservabilityLayer())      # OpenTelemetry
```

### 源码: VariablePool 全局传递
```python
variable_pool = VariablePool()
add_variables_to_pool(variable_pool, default_system_variables())
add_node_inputs_to_pool(variable_pool, node_id=node_id, inputs=user_inputs)
# 文件类型特殊处理
if input_value.get("type") and input_value.get("transfer_method"):
    file = file_factory.build_from_mapping(input_value)
```

### 源码: Block → 节点转换链
```
前端Block → API → graph_config(dict) → NodeConfigDict(Pydantic)
→ DifyNodeFactory.create_node() → Node实例 → GraphEngine
```

**可取**: VariablePool · 多层引擎 · 文件工厂

---

## 5. Agno → 多模态输入 + Fork 分支

### 源码: run() 直接接受媒体
```python
def run(self, input, *,
    audio: Sequence[Audio] = None,     # 🎵
    images: Sequence[Image] = None,    # 🖼️
    videos: Sequence[Video] = None,    # 🎬
    files: Sequence[File] = None,      # 📄
):
```

### 源码: Fork 分支对话
```python
def continue_run(self, *, fork=False,
    continue_from="end", regenerate=False):
    """fork=True: 创建独立分支,不覆盖原会话
       regenerate=True: 重新生成当前响应"""
```

### 源码: 四种工具形态
```python
tools: List[Union[
    Toolkit,      # 工具包(多工具)
    Callable,     # 普通函数
    Function,     # 包装函数
    Dict          # 字典定义
]]
```

**可取**: Fork分支 · 多模态输入 · 工具四种形态

---

## 6. RAGAS → 答案相关性(逆问题生成法)

### 源码: AnswerRelevancy
```python
# 从答案生成N个问题 → 嵌入 → 计算余弦相似度
class ResponseRelevancy:
    strictness: int = 3  # 生成3个问题
    
    def _calculate_score(self, answers, row):
        question = row["user_input"]
        gen_questions = [a.question for a in answers]
        
        # 非承诺答案 → 直接0分
        if all(a.noncommittal for a in answers):
            return 0.0
        
        # 余弦相似度
        cosine_sim = calculate_similarity(question, gen_questions)
        score = cosine_sim.mean()
```

### 核心思路
```
用户问题Q → 答案A → 从A生成3个子问题{q1,q2,q3}
→ embed(Q) · embed(qi) → 余弦相似度均值 = 相关性分数
→ 如果答案模糊("我不知道"), 直接0分
```

**可取**: 逆问题评估法 · 可直接用于我们的 Benchmark

---

## 7. LangGraph → StateGraph + Checkpointer

### 源码: 三种边类型
```python
add_edge("A", "B")                     # 无条件边
add_edge(["A","B"], "C")              # 等待边(多节点汇聚)
add_conditional_edges("A", router_fn,  # 条件边
    {"yes": "B", "no": "C"})
```

### 源码: 节点策略
```python
add_node("process", fn,
    retry_policy=RetryPolicy(max_attempts=3),
    cache_policy=CachePolicy(ttl=60),
    error_handler=error_fn,            # 节点级错误处理
    timeout=30,                        # 节点超时
    defer=True,                        # 延迟执行
)
```

### 源码: Checkpointer 接口
```python
class Checkpointer:
    aget_tuple(config) → CheckpointTuple   # 恢复
    aput(config, checkpoint, metadata)      # 保存
    alist(config, filter, limit)            # 列出
    aput_writes(config, writes, task_id)    # 中间写入
```

### 源码: compile 编译流程
```
图定义 → 验证(validate) → 准备通道 → 
应用默认策略 → 创建CompiledStateGraph →
attach_node/edge/branch → 返回可执行图
```

**可取**: 节点策略系统 · 三边类型 · 编译验证

---

## 8 个可直接实现的源码级改进

| # | 来源 | 具体能力 | 代码量 | 文件 |
|:--:|------|---------|:--:|------|
| 1 | **Mem0** | 实体图谱检索(with惩罚因子) | 150行 | `memory/graph_memory.py` |
| 2 | **LiteLLM** | 预调用检查链(健康/限流/预算) | 100行 | `providers/pre_call_checks.py` |
| 3 | **Dify** | VariablePool(全局变量传递) | 80行 | `core/variable_pool.py` |
| 4 | **Agno** | Fork分支对话 | 50行 | `core/session_manager.py`改进 |
| 5 | **RAGAS** | 逆问题评估法 | 80行 | `tests/benchmark.py`改进 |
| 6 | **LangGraph** | 节点策略(retry/cache/timeout) | 60行 | `core/agent.py`改进 |
| 7 | **Browser-Use** | LLM智能降级 | 40行 | `providers/router.py`改进 |
| 8 | **LiteLLM** | 静默流量镜像(A/B测试) | 40行 | `providers/router.py`改进 |

**总计: ~600 行代码，覆盖 7 个项目的精华。**
