"""Agent Core 测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core.agent import Agent, AgentConfig
from agent.core.exceptions import AgentError, ToolError, ToolNotFoundError
from agent.providers.mock import MockLLM
from agent.tools.builtin import ReadFileTool, ListDirTool, GrepTool


def test_agent_init():
    agent = Agent(AgentConfig(provider="deepseek"))
    assert agent.registry is not None
    assert agent.router is not None


def test_agent_with_mock_llm():
    agent = Agent(AgentConfig(provider="deepseek", max_turns=3))
    agent.register_tools([ReadFileTool(), ListDirTool()])
    agent.llm = MockLLM()
    assert len(agent.registry) == 2


def test_exception_hierarchy():
    e = ToolError("failed", tool_name="bash")
    assert e.tool_name == "bash"
    assert e.recoverable is True
    assert isinstance(e, AgentError)

    e2 = ToolNotFoundError("not found", tool_name="xxx")
    assert isinstance(e2, ToolError)
