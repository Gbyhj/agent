"""
Tool System — 工具注册、调度、执行

设计融合:
- Grok Build: NewTool trait + ToolRegistryBuilder + Resource 依赖注入
- Smolagents: @tool 装饰器 + from_langchain() + from_mcp()
- Cline: Plugin 可注册 tools、监听 lifecycle

工具接口:
  每个工具 = name + description + parameters(JSON Schema) + execute()
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolParam:
    """工具参数定义"""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    enum: list[str] | None = None


class BaseTool(ABC):
    """
    工具基类（参考 Grok Build NewTool trait）

    子类只需实现:
    - name: 工具名称
    - description: 工具描述（LLM 会看到）
    - parameters: 参数列表
    - execute(): 执行逻辑
    """
    name: str = ""
    description: str = ""
    parameters: list[ToolParam] = []
    is_destructive: bool = False  # 是否为破坏性操作（Plan模式会拒绝）

    def to_schema(self) -> dict:
        """生成 OpenAI tool_call JSON Schema"""
        props = {}
        required = []
        for p in self.parameters:
            prop = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            props[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                }
            }
        }

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具逻辑，返回字符串结果"""
        ...

    def __repr__(self):
        return f"Tool({self.name})"


# ── Decorator 风格注册（参考 Smolagents @tool）──
def tool(name: str, description: str, params: list[ToolParam] | None = None,
         is_destructive: bool = False):
    """@tool 装饰器，快速创建工具"""
    params = params or []

    def decorator(func: Callable) -> BaseTool:
        class DecoratedTool(BaseTool):
            def execute(self2, **kwargs) -> str:
                return func(**kwargs)

        DecoratedTool.name = name
        DecoratedTool.description = description
        DecoratedTool.parameters = params
        DecoratedTool.is_destructive = is_destructive
        return DecoratedTool()

    return decorator


class ToolRegistry:
    """
    工具注册中心（参考 Grok Build ToolRegistryBuilder）

    - register(): 注册单个工具
    - register_all(): 批量注册
    - get(): 按名称获取
    - describe_all(): 生成全部工具的 LLM 描述
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册工具（参考 Grok Build register_all()）"""
        if tool.name in self._tools:
            print(f"[Warn] 工具 '{tool.name}' 已存在，将被覆盖")
        self._tools[tool.name] = tool

    def register_all(self, tools: list[BaseTool]):
        """批量注册"""
        for t in tools:
            self.register(t)

    def unregister(self, name: str):
        """移除工具"""
        self._tools.pop(name, None)

    def get(self, name: str) -> BaseTool | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def describe_all(self) -> str:
        """人类可读的工具描述"""
        lines = ["## 可用工具\n"]
        for t in self._tools.values():
            params_desc = ", ".join(f"{p.name}: {p.type}" for p in t.parameters)
            lines.append(f"- **{t.name}**: {t.description}")
            if params_desc:
                lines.append(f"  参数: {params_desc}")
        return "\n".join(lines)

    def to_schema_list(self) -> list[dict]:
        """生成 OpenAI tool_call JSON Schema 列表"""
        return [t.to_schema() for t in self._tools.values()]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self):
        return len(self._tools)

    def __repr__(self):
        return f"ToolRegistry({len(self)} tools: {', '.join(self.list_names())})"
