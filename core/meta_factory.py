"""
Meta Agent Factory — 元 Agent 工厂

灵感: CrewAI 角色系统 × MCP 协议 × SubAgent 协调器

元 Agent 根据任务自动创建专用子 Agent 团队。

用法:
    factory = MetaAgentFactory(llm=agent.llm)
    team = factory.analyze_and_build("做一个电商后端 API")
    
    await team.execute()
    result = team.synthesize()
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WorkerRole:
    """子 Agent 角色定义"""
    name: str              # 角色名
    role: str              # 英文角色
    task: str              # 分配的任务
    tools: list[str]       # 需要的工具
    priority: int = 1      # 优先级（越小越先执行）
    depends_on: list[str] = field(default_factory=list)  # 依赖的其他角色


@dataclass
class TeamPlan:
    """团队执行计划"""
    original_task: str
    analysis: str          # 元 Agent 的分析
    workers: list[WorkerRole]
    parallelism: str       # "sequential" / "parallel" / "mixed"


class MetaAgentFactory:
    """
    元 Agent 工厂

    流程:
    1. 分析任务 → 拆解为子任务
    2. 为每个子任务创建专用 Agent（角色+工具+prompt）
    3. 按依赖关系调度执行（串行依赖，并行独立）
    4. 收集结果 → 合成最终输出
    """

    # 预设角色模板（不需要 LLM 就能匹配）
    ROLE_TEMPLATES = {
        "api": WorkerRole(
            name="API 开发", role="api_dev",
            task="", tools=["read_file", "write_file", "bash", "grep"],
            priority=1,
        ),
        "database": WorkerRole(
            name="数据库设计", role="db_architect",
            task="", tools=["read_file", "write_file", "grep"],
            priority=1,
        ),
        "test": WorkerRole(
            name="测试工程师", role="tester",
            task="", tools=["read_file", "write_file", "bash", "grep"],
            priority=2, depends_on=["api_dev"],
        ),
        "docs": WorkerRole(
            name="文档编写", role="doc_writer",
            task="", tools=["read_file", "write_file", "list_dir"],
            priority=3, depends_on=["api_dev", "db_architect"],
        ),
        "review": WorkerRole(
            name="代码审查", role="code_reviewer",
            task="", tools=["read_file", "grep"],
            priority=2, depends_on=["api_dev"],
        ),
        "refactor": WorkerRole(
            name="重构专家", role="refactor_engineer",
            task="", tools=["read_file", "write_file", "grep", "bash"],
            priority=1,
        ),
        "search": WorkerRole(
            name="信息收集", role="researcher",
            task="", tools=["web_search", "web_fetch", "read_file"],
            priority=1,
        ),
    }

    def __init__(self, llm=None):
        self._llm = llm
        self._tools_registry: dict[str, Any] = {}
        self._history: list[TeamPlan] = []

    def register_tool(self, name: str, tool: Any):
        """注册可用工具"""
        self._tools_registry[name] = tool

    def analyze_task(self, task: str) -> TeamPlan:
        """分析任务并生成团队计划（用规则，不用 LLM）"""
        task_lower = task.lower()
        workers = []
        analysis_parts = []

        # API 相关
        if any(kw in task_lower for kw in ["api", "接口", "后端", "rest", "路由"]):
            w = WorkerRole(
                name="API 开发", role="api_dev",
                task="实现 API 路由和业务逻辑",
                tools=["read_file", "write_file", "bash", "grep"],
                priority=1,
            )
            workers.append(w)
            analysis_parts.append("API 开发")

        # 数据库相关
        if any(kw in task_lower for kw in ["数据库", "database", "表", "model", "schema", "sql"]):
            w = WorkerRole(
                name="数据库设计", role="db_architect",
                task="设计数据库表结构和模型",
                tools=["read_file", "write_file", "grep"],
                priority=1,
            )
            workers.append(w)
            analysis_parts.append("数据库设计")

        # 测试相关
        if any(kw in task_lower for kw in ["测试", "test", "pytest", "单元测试"]):
            w = WorkerRole(
                name="测试工程师", role="tester",
                task="编写单元测试和集成测试",
                tools=["read_file", "write_file", "bash", "grep"],
                priority=2,
                depends_on=[r.role for r in workers if r.role == "api_dev"],
            )
            workers.append(w)
            analysis_parts.append("测试")

        # 文档相关
        if any(kw in task_lower for kw in ["文档", "doc", "readme", "说明"]):
            w = WorkerRole(
                name="文档编写", role="doc_writer",
                task="编写 API 文档和使用说明",
                tools=["read_file", "write_file", "list_dir"],
                priority=3,
                depends_on=[r.role for r in workers if r.role in ("api_dev", "db_architect")],
            )
            workers.append(w)
            analysis_parts.append("文档")

        # 搜索/研究
        if any(kw in task_lower for kw in ["搜索", "查询", "search", "最新", "新闻"]):
            w = WorkerRole(
                name="信息收集", role="researcher",
                task="搜索相关资料和信息",
                tools=["web_search", "web_fetch", "read_file"],
                priority=1,
            )
            workers.append(w)
            analysis_parts.append("信息收集")

        # 如果没有匹配到任何模板，创建通用 worker
        if not workers:
            w = WorkerRole(
                name="通用执行", role="general_worker",
                task=task,
                tools=["read_file", "write_file", "bash", "grep", "web_search"],
            )
            workers.append(w)
            analysis_parts.append("通用任务")

        # 确定并行度
        has_deps = any(w.depends_on for w in workers)
        if len(workers) <= 1:
            parallelism = "sequential"
        elif has_deps:
            parallelism = "mixed"
        else:
            parallelism = "parallel"

        plan = TeamPlan(
            original_task=task,
            analysis=f"拆解为 {len(workers)} 个子任务: {', '.join(analysis_parts)}",
            workers=workers,
            parallelism=parallelism,
        )
        self._history.append(plan)
        return plan

    def build_team_prompt(self, plan: TeamPlan) -> str:
        """构建团队总 prompt"""
        lines = [
            f"# 团队任务: {plan.original_task}",
            f"",
            f"## 分析",
            f"{plan.analysis}",
            f"",
            f"## 团队 ({len(plan.workers)} 成员, {plan.parallelism})",
            f"",
        ]
        for w in plan.workers:
            deps = f" (依赖: {', '.join(w.depends_on)})" if w.depends_on else ""
            lines.append(f"### {w.name} ({w.role})")
            lines.append(f"- 任务: {w.task}")
            lines.append(f"- 工具: {', '.join(w.tools)}")
            lines.append(f"- 优先级: P{w.priority}{deps}")
            lines.append("")

        lines.append("## 执行顺序")
        sorted_workers = sorted(plan.workers, key=lambda w: w.priority)
        for w in sorted_workers:
            lines.append(f"{w.priority}. {w.name}: {w.task}")

        return "\n".join(lines)

    def get_workers_by_priority(self, plan: TeamPlan) -> list[list[WorkerRole]]:
        """按优先级分组（同优先级可并行）"""
        groups: dict[int, list[WorkerRole]] = {}
        for w in plan.workers:
            groups.setdefault(w.priority, []).append(w)
        return [groups[p] for p in sorted(groups.keys())]

    async def execute_plan(self, plan: TeamPlan, executor_fn=None) -> dict:
        """
        执行团队计划
        
        executor_fn: 可选的执行函数，签名为 async def fn(worker: WorkerRole) -> str
        """
        results = {}

        if plan.parallelism == "sequential" or plan.parallelism == "mixed":
            # 按优先级分组执行
            for priority_group in self.get_workers_by_priority(plan):
                tasks = []
                for w in priority_group:
                    # 检查依赖是否完成
                    if w.depends_on:
                        deps_ready = all(d in results for d in w.depends_on)
                        if not deps_ready:
                            continue

                    if executor_fn:
                        tasks.append(executor_fn(w))
                    else:
                        tasks.append(self._default_executor(w))

                if tasks:
                    group_results = await asyncio.gather(*tasks)
                    for w, r in zip(priority_group, group_results):
                        results[w.role] = r
        else:
            # 全并行
            tasks = [executor_fn(w) if executor_fn else self._default_executor(w) for w in plan.workers]
            all_results = await asyncio.gather(*tasks)
            for w, r in zip(plan.workers, all_results):
                results[w.role] = r

        return results

    async def _default_executor(self, worker: WorkerRole) -> str:
        """默认执行器（子代理模式）"""
        # 简化版：返回执行计划
        return f"[{worker.name}] 将使用 {', '.join(worker.tools)} 完成: {worker.task}"

    def synthesize(self, plan: TeamPlan, results: dict) -> str:
        """合成最终输出"""
        lines = [
            f"# 任务完成报告",
            f"",
            f"**原始任务**: {plan.original_task}",
            f"**分析**: {plan.analysis}",
            f"**执行方式**: {plan.parallelism}",
            f"",
            f"## 各角色产出",
            f"",
        ]
        for w in plan.workers:
            result = results.get(w.role, "未执行")
            lines.append(f"### {w.name}")
            lines.append(f"- 状态: {'✅ 完成' if w.role in results else '⏳ 未开始'}")
            lines.append(f"- 产出: {str(result)[:200]}")
            lines.append("")

        lines.append("---")
        lines.append(f"*由元 Agent 工厂自动编排 · {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "total_plans": len(self._history),
            "templates": len(self.ROLE_TEMPLATES),
            "recent": [p.original_task[:50] for p in self._history[-5:]],
        }
