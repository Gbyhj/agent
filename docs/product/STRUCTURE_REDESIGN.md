# 项目结构重构设计

> 从 100+ 文件扁平堆砌 → 5 大模块层级分明

---

## 当前问题

```
agent/                           ← 根目录混乱
├── core/ (18个文件平铺)          ← 太多了，找不到
├── tools/ memory/ providers/    ← OK
├── beta_test.py (测试在根目录)   ← 应该放 tests/
├── synthetic_user_test.py        ← 同上
├── desktop_app.py (产品代码)     ← 应该放 apps/
├── 15个.md文件散落根目录         ← 分类不清
├── gunicorn_config.py (运维)    ← 应该放 deploy/
├── Dockerfile (运维)            ← 同上
├── requirements.txt             ← 同上
└── kb/ (网站文件，但路径独立)     ← 应该属于 apps/
```

---

## 重构后

```
agent/
│
├── src/                          # ══ 主源码 ══
│   ├── __init__.py
│   │
│   ├── engine/                   # 引擎层
│   │   ├── __init__.py
│   │   ├── agent.py              # Agent Loop
│   │   ├── state.py              # AgentState
│   │   ├── codeact.py            # CodeAct 工作流
│   │   ├── code_agent.py         # CodeAgent 模式
│   │   ├── subagent.py           # SubAgent 协调器
│   │   └── shell.py              # CLI Shell
│   │
│   ├── infra/                    # 基础设施层
│   │   ├── __init__.py
│   │   ├── session.py            # 会话管理
│   │   ├── project.py            # 项目状态
│   │   ├── events.py             # 事件总线 + CostTracker
│   │   ├── variables.py          # 变量池 (Dify)
│   │   ├── strategy.py           # 节点策略 (LangGraph)
│   │   ├── flags.py              # Feature Flags
│   │   └── users.py              # 用户系统 + 限流
│   │
│   ├── features/                 # 创新功能层
│   │   ├── __init__.py
│   │   ├── reflex.py             # 条件反射
│   │   ├── growth.py             # 成长AI
│   │   ├── time_travel.py        # 时间旅行
│   │   ├── adversarial.py        # 对抗审查
│   │   ├── meta.py               # 元Agent工厂
│   │   ├── heartbeat.py          # 心跳调度 (OpenClaw)
│   │   └── workflow.py           # 工作流引擎 (Dify)
│   │
│   ├── memory/                   # 记忆系统
│   │   ├── __init__.py
│   │   ├── file.py               # 文件记忆
│   │   ├── vector.py             # 向量记忆 (ChromaDB)
│   │   └── graph.py              # 图谱记忆 (Mem0公式)
│   │
│   ├── tools/                    # 工具系统
│   │   ├── __init__.py
│   │   ├── registry.py           # 工具注册器
│   │   ├── builtin.py            # 内置工具 (6个)
│   │   ├── search.py             # 搜索工具
│   │   ├── export.py             # 导出工具
│   │   └── templates.py          # 任务模板
│   │
│   ├── providers/                # LLM 提供者
│   │   ├── __init__.py
│   │   ├── llm.py                # 统一 LLM 接口
│   │   ├── router.py             # 智能路由
│   │   ├── semantic.py           # 语义难度分析
│   │   ├── checks.py             # 预调用检查链
│   │   └── mock.py               # Mock LLM
│   │
│   ├── mcp/                      # MCP 协议
│   │   ├── __init__.py
│   │   ├── server.py
│   │   └── protocol.py
│   │
│   ├── sandbox/                  # 安全沙箱
│   │   └── __init__.py
│   │
│   ├── observability/            # 可观测
│   │   └── tracer.py
│   │
│   ├── prompt/                   # Prompt 模板
│   │   ├── __init__.py
│   │   └── system/  (3 templates)
│   │
│   ├── shared/                   # 共享基础
│   │   ├── __init__.py
│   │   ├── exceptions.py         # 异常体系
│   │   ├── config.py             # 配置加载
│   │   └── logger.py             # 日志系统
│   │
│   └── server.py                 # API 服务入口
│
├── tests/                        # ══ 测试 ══
│   ├── __init__.py
│   ├── test_core.py              # 核心测试
│   ├── benchmark.py              # 基准测试
│   ├── beta/                     # 内测
│   │   └── test_scenarios.py
│   └── synthetic/                # 合成用户测试
│       └── test_user_journeys.py
│
├── apps/                         # ══ 客户端 ══
│   ├── web/                      # Web UI
│   │   ├── index.html
│   │   ├── agent.html
│   │   ├── logo.svg
│   │   ├── manifest.json
│   │   └── styles.css
│   ├── desktop/                  # 桌面
│   │   └── app.py
│   └── miniapp/                  # 小程序
│       ├── app.json
│       └── pages/
│
├── deploy/                       # ══ 部署 ══
│   ├── Dockerfile
│   ├── compose.yml
│   ├── gunicorn.py
│   └── nginx.conf
│
├── docs/                         # ══ 文档 ══
│   ├── README.md                 # 项目总览
│   ├── AGENTS.md                 # AI 上下文
│   ├── CHANGELOG.md
│   ├── LICENSE
│   │
│   ├── architecture/             # 架构文档
│   │   ├── BLUEPRINT.md
│   │   ├── DESIGN_DOC_TEMPLATE.md
│   │   └── API.md
│   │
│   ├── engineering/              # 工程实践
│   │   ├── CODE_REVIEW.md
│   │   ├── SLO.md
│   │   ├── FEATURE_FLAGS.md
│   │   └── PROJECT_PLAN.md
│   │
│   ├── research/                 # 调研分析
│   │   ├── 25_PROJECTS.md
│   │   ├── SOURCE_ANALYSIS.md
│   │   ├── BEST_OF_BEST.md
│   │   ├── UX_ANALYSIS.md
│   │   └── DESIGN_PATTERNS.md
│   │
│   ├── audits/                   # 审计报告
│   │   ├── EXPERT_REVIEW.md
│   │   ├── EXPERT_FULL.md
│   │   ├── FINAL_AUDIT.md
│   │   └── C_CONSUMER_AUDIT.md
│   │
│   └── product/                  # 产品文档
│       ├── INNOVATIONS.md
│       ├── SURPASS_PLAN.md
│       ├── C_CONSUMER.md
│       ├── LAUNCH_CHECKLIST.md
│       └── PROJECT_SUMMARY.md
│
├── pyproject.toml                # 现代 Python 配置
├── Makefile                      # 常用命令
└── README.md                     # 入口 README
```

---

## 改进对比

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| 根目录文件 | 30+ 混杂 | **3 个** (README/Makefile/pyproject) |
| core/ 平铺 | 18 文件 | **3 子包** (engine/infra/features) |
| 测试位置 | 散落3处 | **tests/** 统一 |
| 产品代码 | 混在src里 | **apps/** 独立 |
| 文档 | 15个在根目录 | **docs/** 5 子目录分类 |
| 部署配置 | 散落 | **deploy/** |
| 导入路径 | agent.core.xxx | **agent.src.xxx** (清晰) |

## 导入变化

```python
# Before
from agent.core.agent import Agent
from agent.core.session_manager import SessionManager
from agent.memory.vector_memory import VectorMemory
from agent.beta_test import BetaUserSimulator

# After  
from agent.src.engine import Agent
from agent.src.infra import SessionManager
from agent.src.memory import VectorMemory
from agent.tests.beta import BetaUserSimulator
```

## 迁移清单

```
Phase 1: 创建新结构 + 移动文件         (30min)
Phase 2: 修复所有 import              (20min)  
Phase 3: 更新 CI + Docker + 启动脚本   (10min)
Phase 4: 运行全部测试验证              (5min)
Phase 5: 部署 + 推送 GitHub            (5min)
```

---

**总文件: 100 → 100 (组织改变，文件数不变)**  
**清晰度: 3/10 → 9/10**
