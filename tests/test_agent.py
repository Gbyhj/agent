import pytest
#!/usr/bin/env python3
"""Agent 快速测试 — 验证核心循环 + 工具系统"""

import asyncio
import sys
sys.path.insert(0, ".")

from agent.core.agent import Agent, AgentConfig
from agent.tools.builtin import (
    ReadFileTool, WriteFileTool, ListDirTool, GrepTool, BashTool,
)


@pytest.mark.asyncio
async def test_tool_registry():
    """测试工具注册系统"""
    print("=== Test 1: Tool Registry ===")
    from agent.core.tool_registry import ToolRegistry, tool, ToolParam

    reg = ToolRegistry()
    reg.register_all([ReadFileTool(), ListDirTool(), GrepTool(), BashTool()])

    assert len(reg) == 4, f"Expected 4 tools, got {len(reg)}"
    assert reg.get("read_file") is not None
    assert reg.get("nonexistent") is None

    schema = reg.to_schema_list()
    assert len(schema) == 4
    assert schema[0]["type"] == "function"

    # Test @tool decorator
    @tool("test_echo", "Echo back input", [ToolParam("text", "string", "text to echo", required=True)])
    def echo(text: str) -> str:
        return f"ECHO: {text}"

    reg.register(echo)
    assert len(reg) == 5
    result = reg.get("test_echo").execute(text="hello")
    assert result == "ECHO: hello"

    print(f"  PASS: {len(reg)} tools registered, schema valid, decorator works")
    print(f"  Tools: {reg.list_names()}")


@pytest.mark.asyncio
async def test_builtin_tools():
    """测试内置工具"""
    print("\n=== Test 2: Builtin Tools ===")

    # ReadFile
    r = ReadFileTool().execute(path="agent/BLUEPRINT.md", start_line=1, end_line=5)
    assert "BLUEPRINT.md" in r, f"ReadFile failed: {r[:100]}"
    print(f"  read_file: OK ({len(r)} chars)")

    # ListDir
    r = ListDirTool().execute(path="agent", pattern="*.py")
    assert ".py" in r, f"ListDir failed: {r[:100]}"
    print(f"  list_dir: OK")

    # Grep
    r = GrepTool().execute(pattern="class Agent", path="agent/core/agent.py")
    assert "agent.py" in r, f"Grep failed: {r[:100]}"
    print(f"  grep: OK")

    # Bash (safe command)
    r = BashTool().execute(command="echo hello agent")
    assert "hello agent" in r, f"Bash failed: {r}"
    print(f"  bash: OK")

    # Bash (dangerous command blocked)
    r = BashTool().execute(command="rm -rf /")
    assert "拒绝" in r, f"Dangerous command not blocked: {r}"
    print(f"  bash(危险拦截): OK")

    print(f"  ALL 5 builtin tool tests PASSED")


@pytest.mark.asyncio
async def test_memory():
    """测试记忆系统"""
    print("\n=== Test 3: Memory System ===")
    from agent.memory.memory import MemorySystem

    mem = MemorySystem()
    soul = mem.read_soul()
    assert "SOUL.md" in soul
    print(f"  SOUL.md: OK ({len(soul)} chars)")

    mem.update_memory("测试", "记忆系统验证通过")
    mem_content = mem.read_memory()
    assert "记忆系统验证通过" in mem_content
    print(f"  MEMORY.md update: OK")

    mem.log_daily("Test run: all systems operational")
    ctx = mem.get_context_for_llm()
    assert "SOUL.md" in ctx
    print(f"  Context injection: OK ({len(ctx)} chars)")

    print(f"  ALL memory tests PASSED")


@pytest.mark.asyncio
async def test_llm_provider():
    """测试 LLM Provider 层"""
    print("\n=== Test 4: LLM Provider ===")
    from agent.providers.llm import LLM

    llm = LLM(provider="deepseek", model="deepseek-v4-flash")
    print(f"  Provider: {llm}")
    assert llm.base_url == "https://api.deepseek.com/v1"
    print(f"  Base URL: OK")

    # Test that it can list models
    models = llm.list_models()
    print(f"  Available models: {len(models)}")
    print(f"  LLM provider test PASSED")


@pytest.mark.asyncio
async def test_agent_smoke():
    """Agent 冒烟测试（无需 API key）"""
    print("\n=== Test 5: Agent Smoke Test (no API) ===")

    config = AgentConfig(provider="deepseek", model="deepseek-v4-flash", max_turns=1)
    agent = Agent(config)
    agent.register_tools([ReadFileTool(), ListDirTool(), GrepTool()])

    assert len(agent.registry) == 3
    assert agent.llm.provider == "deepseek"
    print(f"  Agent init: OK ({len(agent.registry)} tools, {agent.llm})")
    print(f"  Agent smoke test PASSED")


async def main():
    print("=" * 60)
    print("  Agent 测试套件")
    print("=" * 60)

    await test_tool_registry()
    await test_builtin_tools()
    await test_memory()
    await test_llm_provider()
    await test_agent_smoke()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
