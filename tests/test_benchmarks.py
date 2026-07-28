"""三大基准评测测试"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.features.benchmarks import BFCLBenchmark, TauBenchBenchmark, GAIABenchmark, UnifiedBenchmark

class MockAgent:
    def run(self, task, max_turns=5):
        class R:
            final_answer = f"Done: {task[:30]}. Result: verified, checked, OK."
            tool_calls = ["read_file", "web_search", "glob"]
            turns = 2
        return R()

agent = MockAgent()

# BFCL
bfcl = BFCLBenchmark()
bfcl_result = bfcl.evaluate(agent)
print(f'BFCL:     {bfcl_result.rate} · {bfcl_result.score:.0%} · {bfcl_result.grade}级 · {bfcl_result.latency_ms:.0f}ms')

# Tau-Bench
tau = TauBenchBenchmark()
tau_result = tau.evaluate(agent)
print(f'τ-Bench:  {tau_result.rate} · {tau_result.score:.0%} · {tau_result.grade}级 · {tau_result.latency_ms:.0f}ms')

# GAIA
gaia = GAIABenchmark()
gaia_result = gaia.evaluate(agent)
print(f'GAIA:     {gaia_result.rate} · {gaia_result.score:.0%} · {gaia_result.grade}级 · {gaia_result.latency_ms:.0f}ms')

# Unified
unified = UnifiedBenchmark()
report = unified.run_all(agent)
print(f'\n=== 综合报告 ===')
for name, r in report['results'].items():
    print(f'  {name:10s}: {r["rate"]:6s} · {r["score"]} · {r["grade"]}级 · {r["latency"]}')
print(f'  综合: {report["overall"]["grade"]}级 · {report["total_time"]}')
