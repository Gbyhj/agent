"""
Agent Modes — Shadow / Assist / Autonomous

Source: Pento · AgentMelt

Shadow Mode:    后台运行，与人工对比，不实际执行 (零风险)
Assist Mode:    生成草稿，人工确认后执行 (低风险)
Autonomous Mode: 自主执行 + 护栏 (需护栏)
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class AgentMode(Enum):
    SHADOW = "shadow"         # 后台对比，不执行
    ASSIST = "assist"         # 草稿 + 人工确认
    AUTONOMOUS = "autonomous" # 自主执行


@dataclass
class ModeResult:
    """不同模式下 Agent 的执行结果"""
    mode: AgentMode
    plan: str = ""
    diff: str = ""            # Shadow: diff 内容对比
    approved: bool = False    # Assist: 是否已批准
    executed: bool = False    # Autonomous: 是否已执行
    result: Any = None
    human_action: str = ""    # 人工修正内容


class ModeManager:
    """三模式管理器"""

    def __init__(self, mode: AgentMode = AgentMode.AUTONOMOUS):
        self.mode = mode
        self._pending_plans: dict[str, ModeResult] = {}
        self._shadow_log: list[ModeResult] = []

    def switch(self, mode: str):
        self.mode = AgentMode(mode)

    def execute(self, agent, task: str, **kwargs) -> ModeResult:
        """按当前模式执行"""

        if self.mode == AgentMode.SHADOW:
            return self._shadow_run(agent, task, **kwargs)
        elif self.mode == AgentMode.ASSIST:
            return self._assist_run(agent, task, **kwargs)
        else:
            return self._autonomous_run(agent, task, **kwargs)

    def _shadow_run(self, agent, task: str, **kwargs) -> ModeResult:
        """Shadow: 运行但不写文件，只记录差异"""
        result = ModeResult(mode=AgentMode.SHADOW)
        try:
            # Run agent in dry-run mode
            resp = agent.run(task, dry_run=True, **kwargs) if hasattr(agent, "run") else None
            result.plan = str(resp)[:500] if resp else "模拟执行"
            result.diff = "Shadow mode: 未实际写入" if not kwargs.get("dry_run") else "Dry run diff"
            self._shadow_log.append(result)
        except Exception as e:
            result.plan = f"Shadow 执行异常: {e}"
        return result

    def _assist_run(self, agent, task: str, **kwargs) -> ModeResult:
        """Assist: 生成计划，等待批准"""
        result = ModeResult(mode=AgentMode.ASSIST)
        try:
            plan = agent.run(task, plan_only=True, **kwargs) if hasattr(agent, "run") else None
            result.plan = str(plan)[:500] if plan else "待批准的计划"
            plan_id = id(result)
            self._pending_plans[str(plan_id)] = result
            result.result = {"plan_id": str(plan_id), "status": "pending_approval"}
        except Exception as e:
            result.plan = f"计划生成异常: {e}"
        return result

    def approve(self, plan_id: str, agent, task: str, **kwargs) -> ModeResult:
        """批准并执行 Assist 模式下的计划"""
        if plan_id not in self._pending_plans:
            return ModeResult(mode=AgentMode.ASSIST, result={"error": "计划不存在"})

        plan = self._pending_plans.pop(plan_id)
        plan.approved = True
        try:
            resp = agent.run(task, **kwargs) if hasattr(agent, "run") else None
            plan.result = str(resp)[:500] if resp else "执行完成"
            plan.executed = True
        except Exception as e:
            plan.result = f"执行异常: {e}"
        return plan

    def _autonomous_run(self, agent, task: str, **kwargs) -> ModeResult:
        """Autonomous: 直接执行"""
        result = ModeResult(mode=AgentMode.AUTONOMOUS, approved=True, executed=True)
        try:
            resp = agent.run(task, **kwargs) if hasattr(agent, "run") else None
            result.result = str(resp)[:500] if resp else "执行完成"
        except Exception as e:
            result.result = f"执行异常: {e}"
        return result

    def get_shadow_stats(self) -> dict:
        return {"total_runs": len(self._shadow_log), "pending_plans": len(self._pending_plans)}
