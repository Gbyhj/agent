"""
Exception Hierarchy — 结构化异常体系

参考:
- Grok Build: AgentError enum
- Smolagents: AgentError, AgentGenerationError, AgentParsingError, AgentExecutionError
"""
from __future__ import annotations


class AgentError(Exception):
    """Agent 基础异常"""
    def __init__(self, message: str, recoverable: bool = False):
        super().__init__(message)
        self.recoverable = recoverable


class ConfigError(AgentError):
    """配置错误"""


class ModelError(AgentError):
    """LLM 调用错误"""


class ToolError(AgentError):
    """工具执行错误"""
    def __init__(self, message: str, tool_name: str = "", recoverable: bool = True):
        super().__init__(f"[{tool_name}] {message}", recoverable)
        self.tool_name = tool_name


class ToolNotFoundError(ToolError):
    """工具未注册"""


class ToolExecutionError(ToolError):
    """工具执行失败"""


class SandboxError(AgentError):
    """沙箱安全违规"""


class PathTraversalError(SandboxError):
    """路径遍历攻击"""


class PermissionError(SandboxError):
    """权限不足"""


class MemoryError(AgentError):
    """记忆系统错误"""


class MCPError(AgentError):
    """MCP 协议错误"""
