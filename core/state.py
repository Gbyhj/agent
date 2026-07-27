"""
Agent State — 有状态会话管理

设计融合:
- LangGraph: StateGraph + Reducer 模式（每步自动追加）
- Grok Build: 会话五种状态 (Working/IdleResident/Dormant/Completed/DeadFailed)
- OpenClaw: Markdown 文件持久化状态
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentState:
    """Agent 会话状态（参考 LangGraph StateGraph TypedDict）"""
    session_id: str
    task: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 对话历史
    messages: list[dict] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    tool_calls_log: list[dict] = field(default_factory=list)

    # 状态标记
    final_answer: str | None = None
    is_finished: bool = False
    status: str = "idle"  # idle → working → completed / failed

    # 上下文管理（参考 Grok Build auto_compact_threshold）
    context_usage_ratio: float = 0.0
    turn_count: int = 0

    def add_thought(self, text: str):
        self.messages.append({"role": "assistant", "content": text})

    def add_observation(self, tool_name: str, result: str):
        obs = f"[{tool_name}] {result[:500]}"
        self.observations.append(obs)
        self.tool_calls_log.append({"tool": tool_name, "result": result[:1000]})
        self.messages.append({"role": "tool", "name": tool_name, "content": result[:4000]})

    def get_history(self) -> list[dict]:
        """获取对话历史（用于 LLM 上下文）"""
        return self.messages[-20:]  # 最近 20 条

    def get_available_tools(self, registry) -> list:
        """获取可用工具的 JSON Schema"""
        return registry.to_schema_list()

    def compact_context(self):
        """上下文压缩：保留关键信息，清理冗余（参考 Grok Build）"""
        # 保留系统消息 + 最近5轮 + 关键观察
        keep = self.messages[:2]  # 系统消息
        keep += self.messages[-10:]  # 最近 10 条
        self.messages = keep
        self.context_usage_ratio = 0.0

    def to_summary(self) -> str:
        return (
            f"Session {self.session_id}: "
            f"{self.task[:50]}... "
            f"turns={self.turn_count}, "
            f"status={self.status}"
        )


@dataclass
class TurnResult:
    """一个任务回合的结果"""
    session_id: str
    final_answer: str
    turns: int
    observations: list[str]
    tool_calls: list[dict]
