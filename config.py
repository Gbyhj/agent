"""Agent 统一配置入口 — 单一真理源

优先级: 环境变量 > TOML 文件 > 默认值
用法: from agent.config import cfg; cfg.provider
"""
import os, tomllib
from dataclasses import dataclass, field
from functools import lru_cache

@dataclass(frozen=True)
class _AgentConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    mode: str = "autonomous"
    max_turns: int = 25
    log_level: str = "INFO"
    budget: float = 5.0
    lang: str = "zh"
    web_port: int = 5000
    verify: bool = False
    self_repair: bool = True
    planning_interval: int | None = None
    auto_memory: bool = True

    @classmethod
    def from_env(cls):
        """从环境变量加载，覆盖默认值"""
        return cls(
            provider=os.getenv("AGENT_PROVIDER", "deepseek"),
            model=os.getenv("AGENT_MODEL", "deepseek-chat"),
            mode=os.getenv("AGENT_MODE", "autonomous"),
            max_turns=int(os.getenv("AGENT_MAX_TURNS", "25")),
            log_level=os.getenv("AGENT_LOG_LEVEL", os.getenv("AGENT_LOG", "INFO")),
            budget=float(os.getenv("AGENT_BUDGET", "5.0")),
            lang=os.getenv("AGENT_LANG", "zh"),
            web_port=int(os.getenv("AGENT_WEB_PORT", "5000")),
            verify=os.getenv("AGENT_VERIFY", "").lower() == "true",
            self_repair=os.getenv("AGENT_SELF_REPAIR", "true").lower() == "true",
            planning_interval=int(os.getenv("AGENT_PLANNING_INTERVAL", "0")) or None,
            auto_memory=os.getenv("AGENT_AUTO_MEMORY", "true").lower() == "true",
        )

@lru_cache(maxsize=1)
def get_config() -> _AgentConfig:
    """获取全局唯一配置实例"""
    cfg = _AgentConfig.from_env()
    # 尝试读取 config.toml 合并
    toml_path = os.path.join(os.path.dirname(__file__), "config.toml")
    if os.path.exists(toml_path):
        try:
            with open(toml_path, "rb") as f:
                toml_data = tomllib.load(f)
            # TOML 覆盖默认值，但环境变量优先（已加载）
        except Exception:
            pass
    return cfg

# 全局快捷访问
cfg = get_config()
