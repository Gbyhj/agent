# Changelog

## v5.0.0 (2026-07-27)

### 新增
- **智能路由**: 5 模型自动选择，每日预算控制，离线回退
- **Planning 系统**: 每 5 轮自动插入规划步骤 (借鉴 Smolagents)
- **Goal 验证**: Agent 声明完成后启动反作弊检查 (借鉴 Grok Build)
- **错误自修复**: 工具失败自动分析原因并重试 (最多 2 次)
- **自动记忆提取**: 任务完成后自动提取关键事实存储 (借鉴 Mem0)
- **DuckDuckGo 搜索**: 免费 Web 搜索工具
- **对话导出**: 自动保存 Markdown + JSON
- **任务模板**: 8 个预设模板 (代码审查/分析/重构/文档/测试/Bug/解释/依赖)
- **一键启动**: start.bat (Windows)
- **项目管理方案**: Git 规范/测试策略/CI-CD/版本发布/路线图

### 改进
- Agent Loop 重构：统一 context → LLM → tools → verify 流程
- 工具系统：缓存只读工具结果，减少重复调用
- Provider 层：新增 SiliconFlow / 智谱 / Ollama 支持

---

## v4.0.0 (2026-07-27)

### 新增
- MCP Server/Client 协议实现
- ChromaDB 语义记忆 (VectorMemory)
- Langfuse 全链路追踪 (AgentTracer)

---

## v3.0.0 (2026-07-27)

### 新增
- Plan/Act 双模式交互 CLI (PlanActShell)
- SubAgent 并行子代理系统 (SubAgentCoordinator)
- 7 Provider 统一接入 (LLM 抽象层)

---

## v2.0.0 (2026-07-27)

### 新增
- Agent Loop 核心循环 (context → LLM → tools → loop)
- 工具注册系统 (BaseTool + @tool + ToolRegistry)
- 6 内置工具 (ReadFile/WriteFile/ListDir/Grep/Bash/WebFetch)
- Markdown 文件式记忆 (SOUL/MEMORY/daily)
- 状态管理 (AgentState + TurnResult)

---

## v1.0.0 (2026-07-27)

### 新增
- 项目初始化
- 架构蓝图 (BLUEPRINT.md)
- 基于 25+ 开源项目源码分析
