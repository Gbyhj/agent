"""
Langfuse Observability — Agent 全链路追踪

设计融合:
- Langfuse: OTEL 原生 + LLM-as-Judge 评估 + Prompt 管理
- Grok Build: token 成本核算 (1USD=10^10 ticks)
- LiteLLM: OpenTelemetry gen_ai.* 语义约定

使用:
    tracer = AgentTracer(enabled=True)
    with tracer.trace("my-task") as span:
        span.log_llm_call(model="gpt-4o", tokens=500, cost=0.01)
        span.log_tool_call("read_file", {"path": "x.py"})
"""
from __future__ import annotations

import time
import os
import json
from dataclasses import dataclass, field
from typing import Any
from contextlib import contextmanager


@dataclass
class TraceSpan:
    """追踪 Span"""
    name: str
    trace_id: str = ""
    span_id: str = ""
    parent_id: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    metadata: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    children: list[TraceSpan] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time else 0

    def log_event(self, name: str, data: dict | None = None):
        self.events.append({"name": name, "data": data or {}, "time": time.time()})

    def log_llm_call(self, model: str, tokens_in: int = 0, tokens_out: int = 0, cost: float = 0):
        self.events.append({
            "type": "llm_call", "model": model,
            "tokens_in": tokens_in, "tokens_out": tokens_out,
            "cost_usd": round(cost, 8), "time": time.time()
        })

    def log_tool_call(self, tool: str, args: dict, result: str = "", error: str = ""):
        self.events.append({
            "type": "tool_call", "tool": tool, "args": str(args)[:200],
            "result": str(result)[:200], "error": error, "time": time.time(),
        })

    def update(self, metadata: dict):
        self.metadata.update(metadata)

    def end(self):
        self.end_time = time.time()

    def to_dict(self) -> dict:
        return {
            "name": self.name, "trace_id": self.trace_id, "span_id": self.span_id,
            "duration_ms": round(self.duration_ms, 2),
            "metadata": self.metadata, "events": self.events,
            "children": [c.to_dict() for c in self.children],
        }


class AgentTracer:
    """
    Agent 追踪器 — 可接入 Langfuse Cloud 或自托管

    参考: Langfuse Python SDK + OpenTelemetry gen_ai conventions

    三层追踪:
    - Run span: 整个任务执行
    - Turn span: 每个 Agent 轮次
    - Event: LLM 调用 / 工具调用 / 错误
    """

    def __init__(self, enabled: bool = False, public_key: str = "", secret_key: str = "",
                 host: str = ""):
        self.enabled = enabled
        self._langfuse = None
        self._spans: list[TraceSpan] = []

        # 尝试初始化 Langfuse
        if enabled:
            pk = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
            sk = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")
            h = host or os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
            if pk and sk:
                try:
                    from langfuse import Langfuse
                    self._langfuse = Langfuse(public_key=pk, secret_key=sk, host=h)
                except ImportError:
                    pass

    @contextmanager
    def trace(self, name: str, metadata: dict | None = None):
        """创建一个追踪 Span（context manager）"""
        span = TraceSpan(name=name, metadata=metadata or {})
        self._spans.append(span)

        # Langfuse trace
        lf_trace = None
        if self._langfuse:
            try:
                lf_trace = self._langfuse.trace(name=name, metadata=metadata)
            except Exception:
                pass

        try:
            yield span
        finally:
            span.end()
            if lf_trace and self._langfuse:
                try:
                    lf_trace.update(metadata={"duration_ms": span.duration_ms, "events": len(span.events)})
                    self._langfuse.flush()
                except Exception:
                    pass

    def get_summary(self) -> dict:
        """获取追踪摘要"""
        if not self._spans:
            return {"traces": 0}
        return {
            "traces": len(self._spans),
            "total_duration_ms": round(sum(s.duration_ms for s in self._spans), 2),
            "total_llm_calls": sum(len([e for e in s.events if e.get("type") == "llm_call"]) for s in self._spans),
            "total_tool_calls": sum(len([e for e in s.events if e.get("type") == "tool_call"]) for s in self._spans),
            "total_cost_usd": round(sum(
                sum(e.get("cost_usd", 0) for e in s.events if e.get("type") == "llm_call")
                for s in self._spans
            ), 6),
        }
