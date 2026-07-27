# Agent v5 — 智能路由 + 搜索 + 导出 + 模板
# 融合 28 个开源项目最佳设计

from .core.agent import Agent, AgentConfig
from .core.tool_registry import BaseTool, ToolRegistry, ToolParam, tool
from .core.state import AgentState, TurnResult
from .core.subagent import SubAgent, SubAgentCoordinator, SubAgentRequest, SubAgentResult
from .core.shell import PlanActShell
from .memory.memory import MemorySystem, MemoryConfig
from .memory.vector_memory import VectorMemory, MemoryEntry
from .providers.llm import LLM, from_env
from .providers.router import SmartRouter
from .observability.tracer import AgentTracer, TraceSpan
from .mcp.protocol import MCPServer, MCPClient, MCPTool, MCPResource
from .tools.builtin import get_builtin_tools, ReadFileTool, WriteFileTool, ListDirTool, GrepTool, BashTool, WebFetchTool
from .tools.web_search import WebSearchTool
from .tools.templates import TaskTemplates
from .tools.export import ConversationExporter

__all__ = [
    "Agent", "AgentConfig",
    "BaseTool", "ToolRegistry", "ToolParam", "tool",
    "AgentState", "TurnResult",
    "SubAgent", "SubAgentCoordinator", "SubAgentRequest", "SubAgentResult",
    "PlanActShell",
    "MemorySystem", "MemoryConfig",
    "VectorMemory", "MemoryEntry",
    "LLM", "from_env",
    "AgentTracer", "TraceSpan",
    "MCPServer", "MCPClient", "MCPTool", "MCPResource",
    "get_builtin_tools",
    "ReadFileTool", "WriteFileTool", "ListDirTool", "GrepTool", "BashTool", "WebFetchTool",
]
