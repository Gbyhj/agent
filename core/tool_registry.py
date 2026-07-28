"""
Progressive Tool Unlock — 渐进式工具解锁

灵感: Grok Build 工具注册 × 沙箱分级 × 游戏技能树

用法:
    registry = ToolRegistry()
    registry.register(ReadFileTool(), level=0)  # 默认可用
    registry.register(BashTool(), level=2)      # 需要沙箱

    # 获取当前级别可用的工具
    tools = registry.get_active()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class ToolParam:
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    enum: list[str] | None = None


class BaseTool(ABC):
    """工具基类 — 新增 level 属性"""
    name: str = ""
    description: str = ""
    parameters: list[ToolParam] = []
    is_destructive: bool = False
    level: int = 0  # 0=default, 1=confirmed, 2=sandbox, 3=approval

    def to_schema(self) -> dict:
        props = {}
        required = []
        for p in self.parameters:
            prop = {"type": p.type, "description": p.description}
            if p.enum: prop["enum"] = p.enum
            props[p.name] = prop
            if p.required: required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            }
        }

    @abstractmethod
    def execute(self, **kwargs) -> str: ...

    def __repr__(self): return f"Tool({self.name}, L{self.level})"


def tool(name: str, description: str, params: list[ToolParam] | None = None,
         level: int = 0, is_destructive: bool = False):
    params = params or []
    def decorator(func):
        class DecoratedTool(BaseTool):
            def execute(self2, **kwargs) -> str: return func(**kwargs)
        DecoratedTool.name = name
        DecoratedTool.description = description
        DecoratedTool.parameters = params
        DecoratedTool.level = level
        DecoratedTool.is_destructive = is_destructive
        return DecoratedTool()
    return decorator


class ToolRegistry:
    """
    支持渐进式解锁的工具注册中心

    Level 0: 只读探索 (read_file, list_dir, grep)
    Level 1: 信息收集 (web_search, web_fetch)
    Level 2: 代码执行 (bash, write_file)
    Level 3: 危险操作 (docker, deploy, 网络)

    Agent 从 Level 0 开始，根据任务复杂度逐步解锁。
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._level: int = 0  # 当前解锁级别

    def register(self, tool: BaseTool, level: int | None = None):
        if level is not None:
            tool.level = level
        self._tools[tool.name] = tool

    def register_all(self, tools: list[BaseTool]):
        for t in tools: self.register(t)

    def unlock(self, level: int):
        """解锁到指定级别"""
        self._level = max(self._level, level)

    def auto_unlock(self, task: str):
        """根据任务自动解锁"""
        complexity_signals = {
            1: ["搜索", "查阅", "网上", "搜索"],
            2: ["执行", "运行", "修改", "创建", "写入", "实现"],
            3: ["部署", "发布", "docker", "数据库", "生产"],
        }
        for level, keywords in complexity_signals.items():
            if any(kw in task for kw in keywords):
                self.unlock(level)

    def get_active(self) -> list[BaseTool]:
        """获取当前级别可用的工具"""
        return [t for t in self._tools.values() if t.level <= self._level]

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def describe_active(self) -> str:
        """当前可用工具的人类可读描述"""
        tools = self.get_active()
        locked = len(self._tools) - len(tools)
        lines = [f"## 可用工具 (Level {self._level})"]
        if locked > 0:
            descs = {0: "基础探索", 1: "信息收集", 2: "代码执行", 3: "高级操作"}
            next_level = self._level + 1
            next_tools = [t.name for t in self._tools.values() if t.level == next_level]
            if next_tools:
                lines.append(f"🔒 {locked} 个工具锁定。复杂任务将自动解锁: {descs.get(next_level, '')}")
        for t in tools:
            params = ", ".join(f"{p.name}:{p.type}" for p in t.parameters)
            lines.append(f"- {t.name}: {t.description}" + (f" ({params})" if params else ""))
        return "\n".join(lines)

    def to_schema_list(self) -> list[dict]:
        """生成当前可用工具的 OpenAI Schema"""
        return [t.to_schema() for t in self.get_active()]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self): return len(self._tools)
    def __repr__(self): return f"ToolRegistry({len(self)} tools, L{self._level} active)"
