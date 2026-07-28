"""
Pre-Call Checks — LiteLLM 预调用检查链

参考 LiteLLM 源码:
    optional_pre_call_checks = [
        deployment_affinity,     # 用户→部署亲和
        session_affinity,        # 会话粘性
        router_budget_limiting,  # 预算限制
        prompt_caching,          # 提示缓存
        enforce_model_rate_limits, # 速率限制
    ]

我们的精简版四层检查链:
    Health → RateLimit → Budget → Fallback
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    passed: bool
    reason: str = ""
    data: dict = field(default_factory=dict)


class PreCallChain:
    """预调用检查链"""

    def __init__(self, budget_limit: float = 5.0, rate_limit: int = 30,
                 rate_window: int = 60):
        self.budget_limit = budget_limit
        self.rate_limit = rate_limit
        self.rate_window = rate_window
        self._daily_cost = 0.0
        self._daily_tokens = 0
        self._request_times: list[float] = []
        self._fallback_models: list[str] = []
        self._circuit_open: dict[str, bool] = {}  # provider → 熔断

    def set_fallback_models(self, models: list[str]):
        self._fallback_models = models

    def check(self, provider: str, model: str, estimated_tokens: int = 0) -> CheckResult:
        """执行完整检查链"""

        # 1. Health Check — 熔断检查
        if self._circuit_open.get(provider, False):
            return CheckResult(False, f"Provider {provider} 已熔断，请稍后重试")

        # 2. Rate Limit
        now = time.time()
        window_start = now - self.rate_window
        self._request_times = [t for t in self._request_times if t > window_start]
        if len(self._request_times) >= self.rate_limit:
            return CheckResult(False, f"速率限制: {self.rate_limit}次/{self.rate_window}s")

        # 3. Budget Check
        est_cost = estimated_tokens * 0.5 / 1_000_000  # 估算费用
        if self._daily_cost + est_cost > self.budget_limit:
            # 尝试回退到便宜模型
            if self._fallback_models:
                return CheckResult(True, "预算超限，切换到备用模型",
                                   data={"fallback_model": self._fallback_models[0]})

        # 4. All checks passed
        self._request_times.append(now)
        return CheckResult(True, "OK", data={"remaining_budget": self.budget_limit - self._daily_cost})

    def record_cost(self, tokens: int, cost: float):
        """记录实际消费"""
        self._daily_tokens += tokens
        self._daily_cost += cost

    def open_circuit(self, provider: str):
        """打开熔断(连续失败时)"""
        self._circuit_open[provider] = True

    def reset_circuit(self, provider: str):
        """重置熔断"""
        self._circuit_open[provider] = False

    def reset_daily(self):
        """每日重置"""
        self._daily_cost = 0.0
        self._daily_tokens = 0

    def stats(self) -> dict:
        return {
            "daily_cost": round(self._daily_cost, 6),
            "daily_tokens": self._daily_tokens,
            "budget_remaining": round(self.budget_limit - self._daily_cost, 2),
            "rate_used": f"{len(self._request_times)}/{self.rate_limit}",
            "circuit_open": dict(self._circuit_open),
        }
