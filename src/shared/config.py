"""统一配置入口 — 单例 + LRU 缓存"""
from __future__ import annotations

import os
from functools import lru_cache
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """应用配置 (只读)"""
    provider: str = field(default_factory=lambda: os.getenv("AGENT_PROVIDER", "deepseek"))
    model: str = field(default_factory=lambda: os.getenv("AGENT_MODEL", "deepseek-v4-flash"))
    max_turns: int = 6
    planning_interval: int | None = None
    verify: bool = False
    auto_memory: bool = True
    daily_budget: float = float(os.getenv("AGENT_BUDGET", "5.0"))
    log_level: str = field(default_factory=lambda: os.getenv("AGENT_LOG", "INFO"))


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
