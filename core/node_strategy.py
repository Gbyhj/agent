"""
Node Strategies — LangGraph 节点策略

参考 LangGraph StateGraph.add_node():
    retry_policy=RetryPolicy(max_attempts=3)
    cache_policy=CachePolicy(ttl=60)  
    error_handler=error_fn
    timeout=30

Agent 每个步骤都可以配置这些策略。
"""
from __future__ import annotations

import time
import functools
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RetryPolicy:
    """重试策略"""
    max_attempts: int = 3
    initial_delay: float = 0.5       # 初始延迟(秒)
    backoff_factor: float = 2.0      # 退避因子
    max_delay: float = 10.0          # 最大延迟
    retry_on: tuple = (Exception,)   # 哪些异常重试

    def delay_for_attempt(self, attempt: int) -> float:
        return min(self.initial_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)


@dataclass
class CachePolicy:
    """缓存策略"""
    ttl: float = 60.0                # 秒
    key_fn: Callable | None = None   # 自定义 key


@dataclass
class TimeoutPolicy:
    """超时策略"""
    timeout: float = 30.0            # 秒
    fallback: Callable | None = None # 超时后的回退函数


class NodeStrategy:
    """节点策略管理器"""

    def __init__(self):
        self._cache: dict[str, tuple[float, Any]] = {}  # key → (expires_at, value)
        self._retry_stats: dict[str, int] = {}           # key → retry_count

    def execute(self, name: str, fn: Callable, *args,
                retry: RetryPolicy | None = None,
                cache: CachePolicy | None = None,
                timeout: TimeoutPolicy | None = None,
                **kwargs) -> Any:
        """按策略执行节点"""

        # Check cache
        if cache:
            cache_key = cache.key_fn(*args, **kwargs) if cache.key_fn else name
            if cache_key in self._cache:
                expires, value = self._cache[cache_key]
                if time.time() < expires:
                    return value

        # With timeout
        if timeout:
            import signal
            try:
                result = self._with_retry(name, fn, retry, *args, **kwargs)
            except Exception as e:
                if timeout.fallback:
                    return timeout.fallback(*args, **kwargs)
                raise
        else:
            result = self._with_retry(name, fn, retry, *args, **kwargs)

        # Set cache
        if cache:
            cache_key = cache.key_fn(*args, **kwargs) if cache.key_fn else name
            self._cache[cache_key] = (time.time() + cache.ttl, result)

        return result

    def _with_retry(self, name: str, fn: Callable, retry: RetryPolicy | None,
                    *args, **kwargs):
        if not retry:
            return fn(*args, **kwargs)

        last_error = None
        for attempt in range(1, retry.max_attempts + 1):
            try:
                self._retry_stats[name] = attempt - 1
                return fn(*args, **kwargs)
            except retry.retry_on as e:
                last_error = e
                if attempt < retry.max_attempts:
                    delay = retry.delay_for_attempt(attempt)
                    time.sleep(delay)
                else:
                    raise

        raise last_error or RuntimeError(f"Max retries ({retry.max_attempts}) exceeded")

    def get_stats(self) -> dict:
        return {"cache_size": len(self._cache), "retry_stats": dict(self._retry_stats)}

    def clear_cache(self):
        self._cache.clear()
