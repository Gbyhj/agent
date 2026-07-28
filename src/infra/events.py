"""
Event Bus — Grok Build 漏掉的能力

所有 Agent 操作发布事件 → 可观测、可回放、可审计

用法:
    bus = EventBus()
    bus.publish("tool_call", {"tool": "read_file", "path": "agent.py"})
    bus.subscribe("tool_call", handler)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any
import json


@dataclass
class Event:
    type: str
    data: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "agent"


class EventBus:
    """事件总线 — 所有操作过这里"""

    def __init__(self, replay_path: str | None = None):
        self._subscribers: dict[str, list[Callable]] = {}
        self._history: list[Event] = []
        self.replay_path = replay_path or "event_stream.jsonl"
        # 加载历史
        try:
            with open(self.replay_path) as f:
                for line in f:
                    if line.strip():
                        self._history.append(Event(**json.loads(line)))
        except FileNotFoundError:
            pass

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, data: dict, source: str = "agent"):
        event = Event(type=event_type, data=data, source=source)
        self._history.append(event)

        # 通知订阅者
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass

        # 持久化
        try:
            with open(self.replay_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def replay(self, event_type: str | None = None) -> list[Event]:
        """回放事件"""
        if event_type:
            return [e for e in self._history if e.type == event_type]
        return list(self._history)

    def stats(self) -> dict:
        types = {}
        for e in self._history:
            types[e.type] = types.get(e.type, 0) + 1
        return {"total_events": len(self._history), "by_type": types}

    def clear(self):
        self._history.clear()
        try:
            open(self.replay_path, "w").close()
        except Exception:
            pass


# 全局事件总线
bus = EventBus()


# ── Cost Tracker ──
class CostTracker:
    """LiteLLM 的能力: 实时追踪费用"""

    # 参考价格 (per 1M tokens)
    PRICES = {
        "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
        "deepseek-v4-pro":   {"input": 0.55, "output": 1.10},
        "gpt-4o-mini":       {"input": 0.15, "output": 0.60},
        "gpt-4o":            {"input": 2.50, "output": 10.00},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    }

    def __init__(self):
        self._calls: list[dict] = []
        self._total_cost = 0.0
        self._daily_reset = datetime.now().strftime("%Y-%m-%d")

    def record(self, provider: str, model: str, prompt_tokens: int,
               completion_tokens: int):
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._daily_reset:
            self._calls.clear()
            self._total_cost = 0.0
            self._daily_reset = today

        prices = self.PRICES.get(model, {"input": 0.5, "output": 1.0})
        cost = (prompt_tokens * prices["input"] + completion_tokens * prices["output"]) / 1_000_000

        self._calls.append({
            "time": datetime.now().isoformat(),
            "provider": provider, "model": model,
            "tokens": prompt_tokens + completion_tokens,
            "cost": cost,
        })
        self._total_cost += cost

    def daily_cost(self) -> float:
        return round(self._total_cost, 6)

    def daily_tokens(self) -> int:
        return sum(c["tokens"] for c in self._calls)

    def stats(self) -> dict:
        by_model = {}
        for c in self._calls:
            m = c["model"]
            by_model[m] = by_model.get(m, {"calls": 0, "tokens": 0, "cost": 0})
            by_model[m]["calls"] += 1
            by_model[m]["tokens"] += c["tokens"]
            by_model[m]["cost"] += c["cost"]
        return {
            "daily_cost": round(self._total_cost, 6),
            "daily_tokens": self.daily_tokens(),
            "total_calls": len(self._calls),
            "by_model": by_model,
        }
