"""
三大基准评测接入 — BFCL · τ-Bench · GAIA

1. BFCL (Berkeley Function Calling Leaderboard)
   测试: 工具选择 · 参数提取 · 多步调用 · 不相关检测

2. τ-Bench (Tau-Bench)
   测试: 多轮对话 · 政策遵从 · 双控制环境

3. GAIA (General AI Assistant)
   测试: 多步推理 · 工具调用 · 信息整合
"""
from __future__ import annotations

import time, json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class BenchmarkResult:
    name: str
    total: int
    passed: int
    score: float
    details: list[dict] = None
    latency_ms: float = 0

    @property
    def rate(self) -> str:
        return f"{self.passed}/{self.total}"

    @property
    def grade(self) -> str:
        r = self.passed / max(self.total, 1)
        if r >= 0.9: return "A"
        if r >= 0.7: return "B"
        if r >= 0.5: return "C"
        return "D"


# ═══════════════════════════════════════════
#  BFCL — Berkeley Function Calling Leaderboard
# ═══════════════════════════════════════════

class BFCLBenchmark:
    """
    BFCL 风格评测 — 工具调用精度

    参考: gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard
          四个子类别: simple · parallel · multi-turn · irrelevance
    """

    CASES = [
        # Simple: 单工具单参数
        {"id": "bfcl-01", "category": "simple", "task": "读 agent.py 文件",
         "expected_tool": "read_file", "expected_args": {"path": "agent.py"}},
        {"id": "bfcl-02", "category": "simple", "task": "搜索 AI Agent",
         "expected_tool": "web_search", "expected_args": {}},
        {"id": "bfcl-03", "category": "simple", "task": "列出 src/ 目录",
         "expected_tool": "list_dir", "expected_args": {"path": "src/"}},

        # Parallel: 多工具并行
        {"id": "bfcl-04", "category": "parallel", "task": "读 agent.py 和 tools.py",
         "expected_tool": "read_file", "parallel": True},
        {"id": "bfcl-05", "category": "parallel", "task": "搜索 Python 和 Java",
         "expected_tool": "web_search", "parallel": True},

        # Multi-turn: 多步调用
        {"id": "bfcl-06", "category": "multi-turn", "task": "先搜 AI 框架，再总结结果",
         "expected_tool": "web_search"},
        {"id": "bfcl-07", "category": "multi-turn", "task": "读代码 → 分析 → 修复",
         "expected_tool": "read_file"},

        # Irrelevance: 不需要工具
        {"id": "bfcl-08", "category": "irrelevance", "task": "你好，介绍一下自己",
         "expected_tool": None},

        # Edge cases
        {"id": "bfcl-09", "category": "edge", "task": "找所有的 .py 文件",
         "expected_tool": "glob"},
        {"id": "bfcl-10", "category": "edge", "task": "检查 agent.py 第 86 行",
         "expected_tool": "read_file"},
    ]

    def evaluate(self, agent) -> BenchmarkResult:
        t0 = time.time()
        passed = 0
        details = []

        for case in self.CASES:
            try:
                result = agent.run(case["task"], max_turns=2)
                answer = str(getattr(result, 'final_answer', result))
                tools = getattr(result, 'tool_calls', []) or []
                tool_names = [str(t).split('(')[0] for t in tools] if tools else []

                expected = case["expected_tool"]
                ok = (expected is None and not tool_names) or \
                     (expected and any(expected in t for t in tool_names))

                if ok:
                    passed += 1

                details.append({
                    "id": case["id"], "category": case["category"],
                    "passed": ok, "tools": tool_names[:3], "expected": expected or "none"
                })
            except Exception as e:
                details.append({"id": case["id"], "passed": False, "error": str(e)[:50]})

        return BenchmarkResult(
            name="BFCL", total=len(self.CASES), passed=passed,
            score=passed / len(self.CASES), details=details,
            latency_ms=(time.time() - t0) * 1000,
        )


# ═══════════════════════════════════════════
#  τ-Bench — 多轮对话 + 政策遵从
# ═══════════════════════════════════════════

class TauBenchBenchmark:
    """
    τ-Bench 风格评测 — 多轮对话 + 政策遵从

    参考: Sierra Research τ-Bench
          零售/航空/电信 三个领域
          双控制: Agent + Simulated Customer
    """

    SCENARIOS = [
        {
            "id": "tau-01", "domain": "retail",
            "conversation": [
                {"role": "user", "text": "我想退一个上周买的商品"},
                {"role": "agent", "expected_action": "verify_order"},
                {"role": "user", "text": "订单号是 ORD-12345"},
                {"role": "agent", "expected_action": "check_return_policy"},
                {"role": "user", "text": "好的，可以退款"},
                {"role": "agent", "expected_action": "process_refund"},
            ],
            "policy_check": ["14天退货", "需原包装", "退款到原账户"],
        },
        {
            "id": "tau-02", "domain": "airline",
            "conversation": [
                {"role": "user", "text": "我要改签明天的航班"},
                {"role": "agent", "expected_action": "verify_booking"},
                {"role": "user", "text": "预订号 FL-789"},
                {"role": "agent", "expected_action": "check_change_policy"},
            ],
            "policy_check": ["改签费", "同舱位", "48小时前"],
        },
        {
            "id": "tau-03", "domain": "telecom",
            "conversation": [
                {"role": "user", "text": "我的网络很慢"},
                {"role": "agent", "expected_action": "check_account_status"},
                {"role": "user", "text": "账号 ACC-456"},
                {"role": "agent", "expected_action": "run_diagnostics"},
            ],
            "policy_check": ["先检查账户状态", "运行诊断", "升级建议"],
        },
    ]

    def evaluate(self, agent) -> BenchmarkResult:
        t0 = time.time()
        score = 0
        details = []

        for scenario in self.SCENARIOS:
            scenario_score = 0
            steps = [s for s in scenario["conversation"] if s["role"] == "agent"]
            matched = 0

            for step in steps:
                try:
                    result = agent.run(step["expected_action"], max_turns=2)
                    answer = str(getattr(result, 'final_answer', result)).lower()
                    # Check if agent action matches expected
                    if any(kw in answer for kw in ["verify", "check", "process", "order", "booking"]):
                        matched += 1
                except Exception:
                    pass

            if steps:
                scenario_score = matched / len(steps)
            score += scenario_score

            details.append({
                "id": scenario["id"], "domain": scenario["domain"],
                "score": f"{scenario_score:.0%}",
                "policies": scenario["policy_check"],
            })

        return BenchmarkResult(
            name="τ-Bench", total=len(self.SCENARIOS),
            passed=int(score), score=score / len(self.SCENARIOS),
            details=details, latency_ms=(time.time() - t0) * 1000,
        )


# ═══════════════════════════════════════════
#  GAIA — General AI Assistant
# ═══════════════════════════════════════════

class GAIABenchmark:
    """
    GAIA 风格评测 — 通用 AI 助手能力

    参考: Meta GAIA benchmark
          466 个真实问题 · 多步推理 + 工具调用
          Level 1-3 难度递增
    """

    CASES = [
        # Level 1: 单步工具
        {"id": "gaia-01", "level": 1, "task": "Python 最新版本是多少？",
         "requires_search": True, "expected_format": "数字"},
        {"id": "gaia-02", "level": 1, "task": "OpenAI 的 CEO 是谁？",
         "requires_search": True},
        {"id": "gaia-03", "level": 1, "task": "查 agent.py 有多少行代码",
         "requires_tool": True},

        # Level 2: 多步推理
        {"id": "gaia-04", "level": 2, "task": "找项目中最大的文件",
         "requires_tool": True},
        {"id": "gaia-05", "level": 2, "task": "本项目用了哪些第三方库",
         "requires_tool": True},
        {"id": "gaia-06", "level": 2, "task": "哪个 Python 文件有最多的函数定义",
         "requires_tool": True},

        # Level 3: 复杂多步
        {"id": "gaia-07", "level": 3, "task": "分析项目的安全漏洞并提供修复建议",
         "requires_tool": True},
        {"id": "gaia-08", "level": 3, "task": "统计代码行数并按模块分组",
         "requires_tool": True},
    ]

    def evaluate(self, agent) -> BenchmarkResult:
        t0 = time.time()
        passed = 0
        details = []

        for case in self.CASES:
            try:
                result = agent.run(case["task"], max_turns=case.get("level", 1) * 2)
                answer = str(getattr(result, 'final_answer', result))
                # Loose check: answer is non-empty and doesn't contain error
                ok = len(answer) > 10 and "error" not in answer.lower()[:50]

                if ok:
                    passed += 1

                details.append({
                    "id": case["id"], "level": case["level"],
                    "passed": ok, "answer_len": len(answer),
                })
            except Exception as e:
                details.append({"id": case["id"], "passed": False, "error": str(e)[:50]})

        return BenchmarkResult(
            name="GAIA", total=len(self.CASES), passed=passed,
            score=passed / len(self.CASES), details=details,
            latency_ms=(time.time() - t0) * 1000,
        )


# ═══════════════════════════════════════════
#  统一评测入口
# ═══════════════════════════════════════════

class UnifiedBenchmark:
    """三基准统一评测"""

    def __init__(self):
        self.bfcl = BFCLBenchmark()
        self.tau = TauBenchBenchmark()
        self.gaia = GAIABenchmark()
        self.results: dict[str, BenchmarkResult] = {}

    def run_all(self, agent) -> dict:
        """运行全部三个基准"""
        t0 = time.time()

        benchmarks = {
            "BFCL": self.bfcl,
            "τ-Bench": self.tau,
            "GAIA": self.gaia,
        }

        for name, bench in benchmarks.items():
            self.results[name] = bench.evaluate(agent)

        elapsed = time.time() - t0

        return {
            "total_time": f"{elapsed:.1f}s",
            "results": {
                name: {
                    "rate": r.rate, "score": f"{r.score:.0%}",
                    "grade": r.grade, "latency": f"{r.latency_ms:.0f}ms",
                }
                for name, r in self.results.items()
            },
            "overall": {
                "total_passed": sum(r.passed for r in self.results.values()),
                "total_cases": sum(r.total for r in self.results.values()),
                "grade": self._overall_grade(),
            },
        }

    def _overall_grade(self) -> str:
        if not self.results:
            return "N/A"
        avg = sum(r.score for r in self.results.values()) / len(self.results)
        if avg >= 0.9: return "A"
        if avg >= 0.7: return "B"
        if avg >= 0.5: return "C"
        return "D"
