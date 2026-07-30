"""
from agent.src.shared.logger import log
SubAgent System — 子代理并行执行

设计融合:
- Grok Build: SubagentBackend trait (spawn/query/cancel) + Git Worktree 隔离
- Cline: Coordinator→Specialist 模式，每 SubAgent 独立模型+工具+上下文
- CrewAI: role+goal+backstory 声明式定义
- Hermes Agent: RPC 压缩多步流水线

使用:
    coordinator = SubAgentCoordinator()
    result = await coordinator.delegate(
        role="代码审查员",
        task="检查 agent/core/agent.py 的安全性",
        tools=[ReadFileTool(), GrepTool()],
    )
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class SubAgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgentRequest:
    """子代理任务请求（参考 Grok Build SubagentRequest）"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    role: str = "worker"
    task: str = ""
    tools: list = field(default_factory=list)
    model: str = ""
    max_turns: int = 10
    context: str = ""  # 父代理传递的上下文

    status: SubAgentStatus = SubAgentStatus.PENDING
    result: str = ""
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def elapsed(self) -> float:
        if self.finished_at:
            return self.finished_at - self.started_at
        return time.time() - self.started_at if self.started_at else 0


@dataclass
class SubAgentResult:
    """子代理执行结果（参考 Grok Build SubagentResult）"""
    request_id: str
    role: str
    result: str
    error: str = ""
    turns: int = 0
    elapsed: float = 0.0


class SubAgent:
    """
    子代理执行器

    每个 SubAgent 拥有独立上下文，可以分配特定工具集和模型。
    参考 Cline 的 "Coordinator delegates to Specialists" 模式。
    """

    def __init__(self, request: SubAgentRequest, parent_llm=None):
        self.req = request
        self._parent_llm = parent_llm

    async def execute(self) -> SubAgentResult:
        """执行子任务"""
        self.req.status = SubAgentStatus.RUNNING
        self.req.started_at = time.time()

        try:
            # 简化版 Agent Loop（子代理不需要完整功能）
            from ..core.agent import Agent, AgentConfig
            from ..core.tool_registry import ToolRegistry

            # 子代理用父代理的 LLM（或独立模型）
            config = AgentConfig(
                model=self.req.model or self._parent_llm.model if self._parent_llm else "deepseek-v4-flash",
                max_turns=self.req.max_turns,
                mode="act",
            )

            sub_agent = Agent(config)
            sub_agent.llm = self._parent_llm  # 共享 LLM 连接
            if self.req.tools:
                sub_agent.register_tools(self.req.tools)

            task_with_context = self.req.task
            if self.req.context:
                task_with_context = f"上下文:\n{self.req.context}\n\n任务:\n{self.req.task}"

            result = await sub_agent.run(task_with_context, session_id=f"sub_{self.req.id}")

            self.req.status = SubAgentStatus.COMPLETED
            self.req.result = result.final_answer
            self.req.finished_at = time.time()

            return SubAgentResult(
                request_id=self.req.id,
                role=self.req.role,
                result=result.final_answer,
                turns=result.turns,
                elapsed=self.req.elapsed,
            )

        except Exception as e:
            self.req.status = SubAgentStatus.FAILED
            self.req.error = str(e)
            self.req.finished_at = time.time()
            return SubAgentResult(
                request_id=self.req.id,
                role=self.req.role,
                result="",
                error=str(e),
                elapsed=self.req.elapsed,
            )


class SubAgentCoordinator:
    """
    子代理协调器（参考 Grok Build SubagentCoordinator）

    管理多个 SubAgent 的生命周期:
    - delegate(): 委派单个子任务
    - delegate_parallel(): 并行执行多个子任务（参考 CrewAI Crew）
    - cancel(): 取消子任务
    """

    def __init__(self, parent_llm=None):
        self._llm = parent_llm
        self._active: dict[str, SubAgent] = {}
        self._history: list[SubAgentResult] = []

    async def delegate(self, role: str, task: str, tools: list | None = None,
                       context: str = "", max_turns: int = 10) -> SubAgentResult:
        """委派单个子任务"""
        req = SubAgentRequest(role=role, task=task, tools=tools or [],
                              context=context, max_turns=max_turns)
        sa = SubAgent(req, parent_llm=self._llm)
        self._active[req.id] = sa

        log.debug(f"  [SubAgent:{req.id}] {role} → {task[:60]}...")
        result = await sa.execute()

        self._active.pop(req.id, None)
        self._history.append(result)
        log.debug(f"  [SubAgent:{req.id}] done ({result.turns} turns, {result.elapsed:.1f}s)")
        return result

    async def delegate_parallel(self, tasks: list[dict]) -> list[SubAgentResult]:
        """
        并行执行多个子任务（参考 CrewAI 的 Crew.kickoff()）

        tasks = [
            {"role": "审查员", "task": "检查安全性", "tools": [...]},
            {"role": "文档员", "task": "生成文档", "tools": [...]},
        ]
        """
        futures = [
            self.delegate(
                role=t["role"], task=t["task"],
                tools=t.get("tools", []),
                context=t.get("context", ""),
                max_turns=t.get("max_turns", 10),
            )
            for t in tasks
        ]
        return await asyncio.gather(*futures)

    def cancel(self, request_id: str):
        """取消子任务"""
        if request_id in self._active:
            self._active[request_id].req.status = SubAgentStatus.CANCELLED
            self._active.pop(request_id)

    def list_active(self) -> list[str]:
        return list(self._active.keys())

    @property
    def history(self) -> list[SubAgentResult]:
        return self._history
