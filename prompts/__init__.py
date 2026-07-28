"""
Prompt Templates — 版本化 Prompt 管理

目录结构:
    prompts/
    ├── system/
    │   ├── default.txt      # 默认系统提示
    │   ├── code_review.txt  # 代码审查
    │   └── architect.txt    # 架构分析
    ├── few_shot/
    │   └── examples.json    # Few-shot 示例
    └── README.md

用法:
    from agent.prompts import PromptManager
    pm = PromptManager()
    prompt = pm.get("code_review", file="agent.py", context="...")
"""
from __future__ import annotations

import os
import json
from typing import Any


PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


class PromptManager:
    """Prompt 模板管理器"""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or PROMPTS_DIR
        self._cache: dict[str, str] = {}

    def get(self, name: str, **kwargs) -> str:
        """获取 prompt 并填充变量"""
        if name not in self._cache:
            path = os.path.join(self.base_dir, "system", f"{name}.txt")
            if os.path.exists(path):
                self._cache[name] = open(path, encoding="utf-8").read()
            else:
                return self._default_prompt(**kwargs)

        return self._cache[name].format(**kwargs)

    def list(self) -> list[str]:
        """列出所有可用 prompt"""
        system_dir = os.path.join(self.base_dir, "system")
        if not os.path.exists(system_dir):
            return ["default"]
        return [f.replace(".txt", "") for f in os.listdir(system_dir) if f.endswith(".txt")]

    def get_few_shot(self, task_type: str) -> list[dict]:
        """获取 Few-shot 示例"""
        path = os.path.join(self.base_dir, "few_shot", f"{task_type}.json")
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
        return []

    def _default_prompt(self, **kwargs) -> str:
        return """你是自主 AI Agent。

可用工具: {tools}

任务: {task}

请分析任务，选择合适的工具，逐步完成。"""