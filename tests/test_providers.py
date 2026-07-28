"""Provider-layer tests"""
import pytest
from agent.providers.mock import MockLLM, MockResponse
from agent.providers.router import SmartRouter, RouteConfig
from agent.providers.semantic_router import SemanticRouter
from agent.providers.pre_call_checks import PreCallChain

class TestMockLLM:
    def test_returns_response(self):
        llm = MockLLM(["Hello world"])
        resp = llm.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "Hello world"
        assert llm.provider == "mock"
    
    def test_tool_calls(self):
        llm = MockLLM(["test"])
        resp = llm.chat([{"role": "user", "content": "hi"}], 
                        tools=[{"type": "function", "function": {"name": "read_file"}}])
        assert resp.tool_calls is not None or resp.final_answer is not None

class TestSemanticRouter:
    def test_complex_task(self):
        sr = SemanticRouter()
        assert sr.route("重构整个项目的架构设计") == "pro"
    
    def test_simple_task(self):
        sr = SemanticRouter()
        assert sr.route("读一下文件") == "flash"

class TestPreCallChain:
    def test_allows_normal(self):
        pc = PreCallChain(budget_limit=10.0, rate_limit=100)
        result = pc.check("deepseek", "deepseek-v4-flash", 100)
        assert result.passed
    
    def test_circuit_breaker(self):
        pc = PreCallChain(rate_limit=100)
        pc.open_circuit("deepseek")
        result = pc.check("deepseek", "deepseek-v4-flash")
        assert not result.passed
