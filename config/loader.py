"""Config Loader — 从 config.toml 加载配置"""
from __future__ import annotations

import os
import sys

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def load_config(path: str | None = None) -> dict:
    """加载配置文件，环境变量覆盖"""
    config = {
        "agent": {"mode": "act", "max_turns": 25, "planning_interval": 5,
                  "verify_completion": True, "auto_memory": True,
                  "self_repair": True, "daily_budget": 5.0},
        "model": {"provider": "deepseek", "model": "deepseek-v4-flash"},
        "logging": {"level": "INFO"},
        "sandbox": {"enabled": True, "mode": "workspace", "docker_enabled": False},
        "security": {"allowed_paths": [], "blocked_commands": [], "blocked_paths": []},
        "memory": {"vector_enabled": True, "persist_dir": "./.agent_memory", "max_daily_logs": 50},
        "tools": {"read_file": True, "write_file": True, "list_dir": True,
                  "grep": True, "bash": True, "web_fetch": True, "web_search": True},
        "web": {"host": "0.0.0.0", "port": 5000, "debug": False},
    }

    # 尝试加载 config.toml
    if path is None:
        candidates = ["config.toml", "config/config.toml",
                      os.path.expanduser("~/.agent/config.toml")]
        for c in candidates:
            if os.path.exists(c):
                path = c
                break

    if path and os.path.exists(path) and tomllib:
        with open(path, "rb") as f:
            overrides = tomllib.load(f)
            for section, values in overrides.items():
                if section in config and isinstance(values, dict):
                    config[section].update(values)

    # 环境变量覆盖
    env_map = {
        "AGENT_PROVIDER": ("model", "provider"),
        "AGENT_MODEL": ("model", "model"),
        "AGENT_MODE": ("agent", "mode"),
        "AGENT_MAX_TURNS": ("agent", "max_turns"),
        "AGENT_LOG_LEVEL": ("logging", "level"),
        "AGENT_WEB_PORT": ("web", "port"),
    }
    for env_key, (section, key) in env_map.items():
        val = os.environ.get(env_key, "")
        if val:
            try:
                if key in ("max_turns", "port"):
                    val = int(val)
                elif key in ("daily_budget",):
                    val = float(val)
                elif val.lower() in ("true", "false"):
                    val = val.lower() == "true"
                config[section][key] = val
            except (ValueError, TypeError):
                pass

    return config
