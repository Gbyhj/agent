"""
MCP Server/Client — Model Context Protocol

设计融合:
- Anthropic MCP: JSON-RPC 2.0 over stdio/HTTP SSE
- Grok Build: xai-grok-mcp crate (rmcp 2.1, OAuth)
- Smolagents: from_mcp() 直接包装 MCP 工具

MCP 定义了三种能力:
- Tools:    模型可调用的函数（类似 OpenAI function calling）
- Resources: 模型可读取的数据（文件、数据库、API）
- Prompts:   预定义的提示词模板

使用 (Server):
    server = MCPServer("my-server")
    server.add_tool("get_weather", weather_handler)
    server.run_stdio()

使用 (Client):
    client = MCPClient()
    tools = await client.list_tools()
    result = await client.call_tool("get_weather", {"city": "Beijing"})
"""
from __future__ import annotations

import json
import asyncio
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable


# ── JSON-RPC 2.0 消息 ────────────────────────
@dataclass
class JSONRPCRequest:
    jsonrpc: str = "2.0"
    id: int = 0
    method: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class JSONRPCResponse:
    jsonrpc: str = "2.0"
    id: int = 0
    result: Any = None
    error: dict | None = None


# ── MCP Types ──────────────────────────────────
@dataclass
class MCPTool:
    """MCP Tool 定义"""
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)  # JSON Schema


@dataclass
class MCPResource:
    """MCP Resource 定义"""
    uri: str
    name: str = ""
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class MCPPrompt:
    """MCP Prompt 定义"""
    name: str
    description: str = ""
    arguments: list[dict] = field(default_factory=list)


# ── MCP Server ────────────────────────────────
class MCPServer:
    """
    MCP 服务器 — 暴露 Tools/Resources/Prompts 给 AI 模型

    传输方式:
    - stdio:  JSON-RPC over stdin/stdout (标准方式)
    - sse:    HTTP Server-Sent Events
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._tools: dict[str, MCPTool] = {}
        self._tool_handlers: dict[str, Callable] = {}
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompt] = {}
        self._request_id = 0

    # ── 注册 ─────────────────────────────────
    def add_tool(self, name: str, handler: Callable, description: str = "",
                 input_schema: dict | None = None):
        """注册一个 MCP 工具"""
        self._tools[name] = MCPTool(name=name, description=description, input_schema=input_schema or {})
        self._tool_handlers[name] = handler

    def add_tool_from_registry(self, tool):
        """从 Agent BaseTool 注册为 MCP 工具"""
        self.add_tool(
            name=tool.name,
            handler=tool.execute,
            description=tool.description,
            input_schema=tool.to_schema()["function"]["parameters"],
        )

    def add_resource(self, uri: str, name: str = "", description: str = "", mime: str = "text/plain"):
        self._resources[uri] = MCPResource(uri=uri, name=name, description=description, mime_type=mime)

    def add_prompt(self, name: str, description: str = "", arguments: list[dict] | None = None):
        self._prompts[name] = MCPPrompt(name=name, description=description, arguments=arguments or [])

    # ── 协议方法 ─────────────────────────────
    def _handle_request(self, request: dict) -> dict:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", 0)

        handlers = {
            "initialize":         self._handle_initialize,
            "tools/list":         self._handle_tools_list,
            "tools/call":         self._handle_tools_call,
            "resources/list":     self._handle_resources_list,
            "resources/read":     self._handle_resources_read,
            "prompts/list":       self._handle_prompts_list,
            "prompts/get":        self._handle_prompts_get,
        }

        handler = handlers.get(method)
        if not handler:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

        try:
            result = handler(params)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}

    def _handle_initialize(self, params: dict) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": self.name, "version": self.version},
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {},
            }
        }

    def _handle_tools_list(self, params: dict) -> dict:
        return {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in self._tools.values()]}

    def _handle_tools_call(self, params: dict) -> dict:
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = self._tool_handlers.get(tool_name)
        if not handler:
            return {"content": [{"type": "text", "text": f"Tool not found: {tool_name}"}], "isError": True}
        result = handler(**arguments)
        return {"content": [{"type": "text", "text": str(result)}]}

    def _handle_resources_list(self, params: dict) -> dict:
        return {"resources": [{"uri": r.uri, "name": r.name, "description": r.description} for r in self._resources.values()]}

    def _handle_resources_read(self, params: dict) -> dict:
        uri = params.get("uri", "")
        resource = self._resources.get(uri)
        if not resource:
            return {"contents": []}
        # 尝试读取文件
        try:
            with open(uri, encoding="utf-8") as f:
                content = f.read()
            return {"contents": [{"uri": uri, "mimeType": resource.mime_type, "text": content}]}
        except Exception:
            return {"contents": [{"uri": uri, "mimeType": resource.mime_type, "text": file_path}]}

    def _handle_prompts_list(self, params: dict) -> dict:
        return {"prompts": [{"name": p.name, "description": p.description} for p in self._prompts.values()]}

    def _handle_prompts_get(self, params: dict) -> dict:
        name = params.get("name", "")
        prompt = self._prompts.get(name)
        if not prompt:
            return {"messages": []}
        return {"description": prompt.description, "messages": []}

    # ── 传输层 ──────────────────────────────
    def run_stdio(self):
        """JSON-RPC over stdin/stdout (标准 MCP 传输)"""
        import sys
        print(f"MCP Server '{self.name}' v{self.version} running on stdio", file=sys.stderr)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self._handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}), flush=True)

    def describe(self) -> str:
        """生成人类可读的服务器描述"""
        lines = [f"MCP Server: {self.name} v{self.version}", ""]
        lines.append(f"Tools ({len(self._tools)}):")
        for t in self._tools.values():
            lines.append(f"  - {t.name}: {t.description}")
        lines.append(f"\nResources ({len(self._resources)}):")
        for r in self._resources.values():
            lines.append(f"  - {r.name}: {r.uri}")
        return "\n".join(lines)


# ── MCP Client ────────────────────────────────
class MCPClient:
    """
    MCP 客户端 — 连接 MCP Server 并调用其工具

    使用:
        client = MCPClient()
        await client.connect_stdio("python mcp_server.py")
        tools = await client.list_tools()
    """

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._request_id = 0

    async def connect_stdio(self, command: str):
        """通过 stdio 连接 MCP Server"""
        self._process = subprocess.Popen(
            command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        # Initialize
        await self._call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})

    async def list_tools(self) -> list[dict]:
        resp = await self._call("tools/list", {})
        return resp.get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> dict:
        return await self._call("tools/call", {"name": name, "arguments": arguments})

    async def list_resources(self) -> list[dict]:
        resp = await self._call("resources/list", {})
        return resp.get("resources", [])

    async def _call(self, method: str, params: dict) -> dict:
        self._request_id += 1
        request = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}

        if self._process and self._process.stdin:
            self._process.stdin.write(json.dumps(request) + "\n")
            self._process.stdin.flush()
            response_line = self._process.stdout.readline()
            return json.loads(response_line).get("result", {})

        return {}

    def close(self):
        if self._process:
            self._process.terminate()
            self._process = None
