"""
Feature Flags — 灰度发布系统

参考: Meta A/B Testing · Google Canary Releases

用法:
    flags = FeatureFlags()
    
    @flags.gate("new_router")
    def task_with_new_router(): ...
    
    if flags.is_enabled("sse_streaming", user_id):
        return stream_response()
"""
from __future__ import annotations

import os
import json
import random
from datetime import datetime


class FeatureFlags:
    """
    功能开关系统

    四种策略:
    - boolean: 全开/全关
    - percentage: 按百分比灰度
    - user_list: 白名单用户
    - a_b_test: A/B 测试（50/50 分流）
    """

    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or os.path.expanduser("~/.agent_flags.json")
        self._flags: dict = self._load()

    def _load(self) -> dict:
        defaults = {
            "sse_streaming":     {"enabled": True,  "strategy": "boolean"},
            "new_router":        {"enabled": True,  "strategy": "boolean"},
            "code_agent_mode":   {"enabled": True,  "strategy": "percentage", "percentage": 50},
            "adversarial_review": {"enabled": True, "strategy": "boolean"},
            "reflex_system":     {"enabled": True,  "strategy": "boolean"},
            "growth_tracking":   {"enabled": True,  "strategy": "boolean"},
        }
        if os.path.exists(self.config_path):
            try:
                loaded = json.load(open(self.config_path, encoding="utf-8"))
                defaults.update(loaded)
            except Exception:
                pass
        return defaults

    def _save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._flags, f, indent=2)

    def is_enabled(self, flag_name: str, user_id: str = "") -> bool:
        """检查功能是否对当前用户开启"""
        flag = self._flags.get(flag_name, {"enabled": False, "strategy": "boolean"})

        if not flag.get("enabled", False):
            return False

        strategy = flag.get("strategy", "boolean")

        if strategy == "boolean":
            return True

        if strategy == "percentage":
            pct = flag.get("percentage", 50)
            # 用 user_id hash 保证同一用户结果一致
            seed = hash(user_id or str(random.random())) % 100
            return seed < pct

        if strategy == "user_list":
            allowlist = flag.get("user_ids", [])
            return user_id in allowlist

        return False

    def enable(self, flag_name: str, **kwargs):
        self._flags[flag_name] = {"enabled": True, **kwargs}
        self._save()

    def disable(self, flag_name: str):
        self._flags[flag_name] = {"enabled": False}
        self._save()

    def set_percentage(self, flag_name: str, percentage: int):
        self._flags[flag_name] = {"enabled": True, "strategy": "percentage", "percentage": percentage}
        self._save()

    def add_user(self, flag_name: str, user_id: str):
        flag = self._flags.get(flag_name, {"enabled": True, "strategy": "user_list", "user_ids": []})
        flag.setdefault("user_ids", []).append(user_id)
        self._flags[flag_name] = flag
        self._save()

    def list_all(self) -> dict:
        return {k: v for k, v in self._flags.items()}

    def gate(self, flag_name: str):
        """装饰器：功能开关门控"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if self.is_enabled(flag_name):
                    return func(*args, **kwargs)
                return None
            return wrapper
        return decorator
