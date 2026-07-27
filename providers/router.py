"""
Smart Model Router — 智能模型路由

根据任务复杂度自动选择最优模型：
- simple:  DeepSeek Flash（¥0.5/M）— 读文件、列出目录
- medium:  DeepSeek Flash 大窗口 — 搜索、分析
- complex: DeepSeek Pro（¥2/M）— 重构、架构设计
- code:    Qwen3-Coder（免费）— 写代码
- offline: Ollama 本地 — 无网络时

用法:
    router = SmartRouter()
    model = router.route("重构 agent/core/agent.py")
    response = model.chat(messages)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .llm import LLM


@dataclass
class RouteConfig:
    """路由配置"""
    name: str
    provider: str
    model: str
    max_tokens: int
    cost_per_mtok: float  # 每百万 token 成本（元）
    priority: int  # 优先级，越小越优先用于简单任务


class SmartRouter:
    """
    智能模型路由器

    路由规则:
    1. 含 "重构/架构/设计/实现" → complex
    2. 含 "写/创建/生成代码" → code (Qwen)
    3. 任务长度 < 30 字 → simple
    4. 默认 → medium

    离线 fallback:
    - 所有 API 不可用 → Ollama 本地

    成本控制:
    - 每日预算 ¥5
    - 超出预算 → 降级到免费模型
    """

    ROUTES = [
        RouteConfig("simple",  "deepseek",   "deepseek-v4-flash",  2048, 0.5,  1),
        RouteConfig("medium",  "deepseek",   "deepseek-v4-flash",  4096, 0.5,  2),
        RouteConfig("complex", "deepseek",   "deepseek-v4-pro",    8192, 2.0,  3),
        RouteConfig("code",    "siliconflow","Qwen/Qwen3-Coder-Plus", 8192, 0.0, 2),
        RouteConfig("offline", "ollama",     "qwen3-coder",        4096, 0.0,  99),
    ]

    CODE_KEYWORDS = [
        "写代码", "实现", "创建", "生成", "编写", "开发",
        "implement", "create", "generate", "write code", "build",
    ]

    COMPLEX_KEYWORDS = [
        "重构", "架构", "设计", "优化性能", "大规模",
        "refactor", "architecture", "design", "optimize",
    ]

    def __init__(self, daily_budget: float = 5.0, _cost_tracker: dict | None = None):
        self.daily_budget = daily_budget
        self._cost_tracker = _cost_tracker or {"spent": 0.0, "calls": 0}

    def route(self, task: str) -> LLM:
        """根据任务自动选择模型"""
        task_lower = task.lower()

        # 1. 复杂任务
        if any(kw in task_lower for kw in self.COMPLEX_KEYWORDS):
            return self._get_llm("complex")

        # 2. 代码生成
        if any(kw in task_lower for kw in self.CODE_KEYWORDS):
            code_llm = self._get_llm("code")
            if code_llm:
                return code_llm
            return self._get_llm("medium")

        # 3. 简单任务
        if len(task) < 30:
            return self._get_llm("simple")

        # 4. 默认
        return self._get_llm("medium")

    def _get_llm(self, route_name: str) -> LLM | None:
        """获取指定路由的 LLM，预算超限时降级"""
        for r in self.ROUTES:
            if r.name == route_name:
                # 预算检查
                if r.cost_per_mtok > 0 and self._cost_tracker["spent"] >= self.daily_budget:
                    # 降级到免费模型
                    for fallback in self.ROUTES:
                        if fallback.cost_per_mtok == 0 and fallback.priority <= r.priority:
                            print(f"  [Router] 预算超限 (¥{self._cost_tracker['spent']:.2f}/{self.daily_budget}), 降级到 {fallback.name}")
                            return LLM(provider=fallback.provider, model=fallback.model)

                api_key = os.environ.get(f"{r.provider.upper()}_API_KEY", "")
                if not api_key and r.provider == "siliconflow":
                    api_key = os.environ.get("SILICONFLOW_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
                # 尝试回退
                if not api_key and r.cost_per_mtok > 0:
                    continue

                print(f"  [Router] → {r.name}: {r.provider}/{r.model} (¥{r.cost_per_mtok}/M tokens)")
                return LLM(provider=r.provider, model=r.model, api_key=api_key)

        # 最终 fallback: Ollama 本地
        for r in self.ROUTES:
            if r.name == "offline":
                print(f"  [Router] → offline: {r.provider}/{r.model}")
                return LLM(provider=r.provider, model=r.model)

        return LLM(provider="deepseek", model="deepseek-v4-flash")

    def get_route_info(self, task: str) -> dict:
        """获取路由决策信息"""
        llm = self.route(task)
        return {
            "task": task[:50],
            "provider": llm.provider,
            "model": llm.model,
            "cost": f"¥{llm.provider}/{llm.model}",
        }

    @property
    def spent_today(self) -> float:
        return self._cost_tracker.get("spent", 0.0)
