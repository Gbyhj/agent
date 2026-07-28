"""
Mock LLM — 用于测试，不消耗 API 额度

用法:
    mock = MockLLM(responses=["我来分析...", None, "完成"])
    llm = LLM(provider="mock")  # 自动使用 MockLLM
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MockResponse:
    content: str | None = None
    tool_calls: list[dict] | None = None
    final_answer: str | None = None
    usage: dict | None = None


class MockLLM:
    """模拟 LLM，用于测试"""

    def __init__(self, responses: list[str | None] | None = None):
        self.responses = responses or ["测试完成。所有功能正常运行。"]
        self._idx = 0
        self.call_count = 0
        self.last_messages: list[dict] = []

    def chat(self, messages: list[dict], tools: list[dict] | None = None, stream: bool = False) -> MockResponse:
        self.last_messages = messages
        self.call_count += 1

        if self._idx < len(self.responses):
            content = self.responses[self._idx]
            self._idx += 1
        else:
            content = "完成"

        resp = MockResponse(content=content, usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})

        if tools and self._idx <= 2:
            resp.tool_calls = [{"name": tools[0]["function"]["name"], "args": {"path": "test.py"}}]

        if self._idx >= len(self.responses) or not tools:
            resp.final_answer = resp.content

        return resp

    def __repr__(self):
        return "MockLLM"
