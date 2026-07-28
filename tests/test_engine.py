"""Engine-layer tests"""
import pytest
from agent.core.agent import Agent, AgentConfig
from agent.core.state import AgentState, TurnResult
from agent.core.codeact import CodeActWorkflow, CodeActPhase
from agent.providers.mock import MockLLM

class TestAgentState:
    def test_init(self):
        s = AgentState(session_id="test", task="analyze")
        assert s.session_id == "test"
        assert s.task == "analyze"
        assert not s.is_finished
    
    def test_add_thought(self):
        s = AgentState(session_id="t", task="t")
        s.add_thought("Plan: analyze")
        assert len(s.messages) == 1

class TestCodeActWorkflow:
    def test_phases_exist(self):
        for phase in CodeActPhase:
            prompt = CodeActWorkflow.get_phase_prompt(phase)
            tools = CodeActWorkflow.get_phase_tools(phase)
            assert len(prompt) > 0
            assert len(tools) > 0
    
    def test_describe(self):
        desc = CodeActWorkflow.describe()
        assert "EXPLORE" in desc
        assert "IMPLEMENT" in desc

class TestAgentWithMock:
    @pytest.mark.asyncio
    async def test_basic_run(self):
        mock = MockLLM(["测试任务完成。"])
        config = AgentConfig(provider="mock", model="mock", max_turns=2,
                            verify_completion=False, planning_interval=None)
        agent = Agent(config)
        agent.llm = mock
        result = await agent.run("test")
        assert result.turns > 0
        assert result.final_answer is not None
        assert "测试" in str(result.final_answer)
    
    @pytest.mark.asyncio
    async def test_returns_result(self):
        mock = MockLLM(["完成"])
        config = AgentConfig(provider="mock", model="mock", max_turns=1,
                            verify_completion=False, planning_interval=None)
        agent = Agent(config)
        agent.llm = mock
        result = await agent.run("test task")
        assert isinstance(result, TurnResult)
        assert result.turns == 1
