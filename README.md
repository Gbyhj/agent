# Agent v5

> 自主 AI Agent — 融合 25+ 开源项目最佳设计

## 快速开始

```bash
# 一键启动（Windows）
start.bat

# 或命令行
python -m agent.main "分析项目架构"
```

## 核心能力

- **智能路由** — 5 模型自动选择，¥5/天预算
- **Planning** — 每 5 轮自动规划
- **Goal 验证** — 反作弊检查
- **自修复** — 工具失败自动重试
- **自动记忆** — 对话经验自动积累
- **免费搜索** — DuckDuckGo
- **SubAgent** — 并行子代理
- **MCP 协议** — 标准工具扩展

## 运行模式

```bash
# 交互模式
python -m agent.main

# 任务模板
python -m agent.main --template code-review --target .

# 指定模型
python -m agent.main "任务" --provider deepseek --model deepseek-v4-pro

# Web UI
python server.py

# 测试
python -m agent.main --test
```

## 项目结构

```
agent/
├── core/          # 核心引擎
├── tools/         # 工具层
├── memory/        # 记忆层
├── providers/     # LLM 接入
├── observability/ # 可观测性
├── mcp/           # MCP 协议
├── server.py      # Web API
├── main.py        # CLI
└── start.bat      # 一键启动
```

## 文档

- [架构蓝图](BLUEPRINT.md)
- [专家评审方案](EXPERT_REVIEW.md)
- [项目管理方案](PROJECT_PLAN.md)
- [源码设计模式](https://agent.保康.top/projects/design-patterns.md)
- [知识库](https://agent.保康.top/kb)

## 许可

MIT
