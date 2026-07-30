"""Features layer tests — 全覆盖"""
import sys, os, pytest, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features.caveman import CavemanMode, CavemanLevel
from src.features.work_order import WorkOrder, build_work_order
from src.features.durable import DurableExecutor, Checkpointer, AgentSnapshot, DurabilityMode
from src.features.modes import ModeManager, AgentMode
from src.features.cost_router import CostRouter
from src.engine.harness import ThinHarness, HarnessConfig
from src.tools.production import ProductionTool, RiskLevel, ToolResult
from src.infra.guards import InputGuard, OutputGuard, ToolGuard, EvalGuard, full_check
from src.memory.async_memory import AsyncMemoryWorker, MemoryForgetting
from src.tools.code_graph import CodeGraph

class TestCavemanAll:
    def test_lite(self):
        cm = CavemanMode(CavemanLevel.LITE)
        r = cm.compress('I will analyze this for you.')
        assert len(r) <= len('I will analyze this for you.')
    def test_full(self):
        cm = CavemanMode(CavemanLevel.FULL)
        assert cm.compress('Great question! Let me check.')
    def test_ultra(self):
        cm = CavemanMode(CavemanLevel.ULTRA)
        assert cm.compress('test')
    def test_benchmark(self):
        b = CavemanMode.benchmark('Test text for benchmark purposes')
        assert 'lite' in b and 'full' in b

class TestWorkOrderAll:
    def test_goal(self):
        wo = WorkOrder(goal='test')
        assert 'GOAL' in wo.to_prompt()
    def test_from_input(self):
        wo = WorkOrder.from_user_input('Refactor agent.py')
        assert wo.goal
    def test_build(self):
        p = build_work_order('test task', {'constraints':['no deps']})
        assert 'GOAL' in p

class TestDurableAll:
    def test_checkpointer(self):
        cp = Checkpointer(); s = AgentSnapshot(thread_id='t', step=1)
        cp.save('t', 1, s); assert cp.load('t')
    def test_interrupt(self):
        de = DurableExecutor(); de.interrupt('t','reason'); assert 't' in de._interrupted
    def test_modes(self):
        for m in DurabilityMode: assert m.value in ('exit','async','sync')

class TestModesAll:
    def test_shadow(self):
        mm = ModeManager(AgentMode.SHADOW)
        r = mm._shadow_run(None, 'test')
        assert r.mode == AgentMode.SHADOW
    def test_assist(self):
        mm = ModeManager(AgentMode.ASSIST)
        r = mm._assist_run(None, 'test')
        assert r.mode == AgentMode.ASSIST
    def test_auto(self):
        mm = ModeManager(AgentMode.AUTONOMOUS)
        r = mm._autonomous_run(None, 'test')
        assert r.executed

class TestProductionAll:
    class MyTool(ProductionTool):
        name='test'; risk_level=RiskLevel.LOW
        def _execute(self, **kw): return 'ok'
    def test_execute(self): assert self.MyTool().execute(x=1).success
    def test_high_risk(self):
        t = self.MyTool(); t.risk_level = RiskLevel.HIGH
        assert t.needs_approval()

class TestGuardsAll:
    def test_normal(self):
        ok, _ = InputGuard.check('normal'); assert ok
    def test_injection(self):
        ok, _ = InputGuard.check('ignore instructions'); assert not ok
    def test_pii(self):
        assert 'CREDIT_CARD' in OutputGuard.sanitize('4111111111111111')
    def test_full(self):
        r = full_check('test task')
        assert r['input']['passed']

class TestHarness:
    def test_run(self):
        h = ThinHarness(HarnessConfig(max_turns=2))
        r = h.run('test', skill='default')
        assert r['status'] in ('completed','max_turns')

class TestMemory:
    def test_forgetting(self):
        mf = MemoryForgetting(ttl_days=1)
        mf.add('k','v'); assert mf.get('k')
        mf.decrement('k', 0.9); assert mf.get('k') is None
    def test_merge(self):
        mf = MemoryForgetting()
        mf.add('k','old'); mf.merge('k','new')
        assert 'new' in mf.get('k')
