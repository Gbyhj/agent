"""Infrastructure tests"""
import pytest
from agent.core.feature_flags import FeatureFlags
from agent.core.variable_pool import VariablePool
from agent.core.node_strategy import NodeStrategy, RetryPolicy, CachePolicy
from agent.core.event_bus import EventBus, CostTracker
from agent.memory.graph_memory import GraphMemory
import os, tempfile

class TestFeatureFlags:
    def test_enable_disable(self):
        ff = FeatureFlags(config_path=tempfile.mktemp())
        ff.enable("test_flag")
        assert ff.is_enabled("test_flag")
        ff.disable("test_flag")
        assert not ff.is_enabled("test_flag")
    
    def test_percentage_rollout(self):
        ff = FeatureFlags(config_path=tempfile.mktemp())
        ff.set_percentage("test", 100)
        assert ff.is_enabled("test", "user_1")

class TestVariablePool:
    def test_set_and_resolve(self):
        vp = VariablePool()
        vp.set_node_output("agent", "answer", "hello")
        assert vp.resolve("agent.answer") == "hello"
    
    def test_template(self):
        vp = VariablePool()
        vp.set_node_output("agent", "result", "world")
        assert vp.resolve_template("Result: {agent.result}") == "Result: world"

class TestNodeStrategy:
    def test_retry(self):
        ns = NodeStrategy()
        calls = [0]
        def flaky():
            calls[0] += 1
            if calls[0] < 2: raise RuntimeError("flaky")
            return "ok"
        result = ns.execute("test", flaky, retry=RetryPolicy(max_attempts=3, initial_delay=0.001))
        assert result == "ok"
        assert calls[0] == 2
    
    def test_cache(self):
        ns = NodeStrategy()
        calls = [0]
        def cached():
            calls[0] += 1
            return calls[0]
        r1 = ns.execute("c", cached, cache=CachePolicy(ttl=99))
        r2 = ns.execute("c", cached, cache=CachePolicy(ttl=99))
        assert r1 == 1 and r2 == 1
        assert calls[0] == 1

class TestEventBus:
    def test_publish_subscribe(self):
        bus = EventBus()
        received = []
        bus.subscribe("test", lambda e: received.append(e.data["msg"]))
        bus.publish("test", {"msg": "hello"})
        assert "hello" in received
        assert len(bus.replay("test")) >= 1

class TestGraphMemory:
    def test_link_and_search(self):
        gm = GraphMemory(path=tempfile.mktemp())
        gm.link("m1", [{"type": "技术", "data": "Python"}])
        gm.link("m2", [{"type": "框架", "data": "Flask"}])
        boosts = gm.boost_search("Python", [("m1", 0.9), ("m2", 0.5)])
        assert "m1" in boosts
