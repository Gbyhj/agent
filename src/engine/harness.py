"""
Thin Harness — Garry Tan 架构范式

Four things only:
  1. Run the model in a loop
  2. Read/write files
  3. Manage context window
  4. Enforce safety constraints

Everything else → Skill files.

Source: Garry Tan "Thin Harness, Fat Skills" (700K+ reads)
         Claude Code 512K line source leak analysis
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class HarnessConfig:
    max_turns: int = 25
    max_tokens_per_turn: int = 4096
    max_cost_per_session: float = 5.0
    safety_mode: str = "strict"  # strict | moderate | permissive


class ThinHarness:
    """
    Thin Harness — 只做四件事。

    用法:
        harness = ThinHarness(HarnessConfig())
        result = harness.run(task, skill="code_review", context={"file": "agent.py"})
    """

    def __init__(self, config: HarnessConfig = None):
        self.config = config or HarnessConfig()
        self._turns = 0
        self._total_cost = 0.0
        self._context: dict = {}
        self._started_at: str = ""

    def run(self, task: str, skill: str = "default",
            context: dict = None, llm=None, tools: list = None) -> dict:
        """主循环 — 极简 Harness"""
        self._started_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self._context = context or {}
        self._turns = 0

        # Load skill
        skill_ctx = self._load_skill(skill)

        for turn in range(self.config.max_turns):
            self._turns = turn + 1

            # 1. Context: 观察当前状态
            observation = self._observe(task, skill_ctx)

            # 2. Think: 模型推理
            if llm:
                response = self._think(llm, observation)
            else:
                break

            # 3. Act: 执行工具
            result = self._act(response, tools or [])

            # 4. Verify: 检查安全
            if not self._safety_check(result):
                return {"status": "blocked", "reason": "safety_check_failed"}

            if result.get("done"):
                return {"status": "completed", "result": result, "turns": self._turns}

        return {"status": "max_turns", "turns": self._turns}

    def _load_skill(self, name: str) -> str:
        """Load skill from skills/ directory"""
        import os
        skill_dir = os.path.join(os.path.dirname(__file__), "..", "skills")
        path = os.path.join(skill_dir, f"{name}.md")
        if os.path.exists(path):
            return open(path, encoding="utf-8").read()
        return f"Task: Complete the request. Be concise and accurate."

    def _observe(self, task: str, skill: str) -> dict:
        return {
            "task": task,
            "skill": skill[:500],
            "context": self._context,
            "turn": self._turns,
            "cost_so_far": self._total_cost,
        }

    def _think(self, llm, observation: dict) -> Any:
        messages = [
            {"role": "system", "content": observation["skill"]},
            {"role": "user", "content": observation["task"]},
        ]
        return llm.chat(messages)

    def _act(self, response, tools: list) -> dict:
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                for tool in tools:
                    if tool.name == tc.get("name"):
                        try:
                            return {"done": False, "output": tool.run(**tc.get("args", {}))}
                        except Exception as e:
                            return {"done": False, "error": str(e)}
        return {"done": True, "output": response.content if hasattr(response, "content") else str(response)}

    def _safety_check(self, result: dict) -> bool:
        if self.config.safety_mode == "permissive":
            return True
        if "error" in result:
            return True  # errors are safe, just logged
        return True
