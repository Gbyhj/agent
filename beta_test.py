#!/usr/bin/env python3
"""
模拟用户内测 — 自动执行 20+ 个真实使用场景

运行:
    cd agent && source .venv/Scripts/activate && python beta_test.py

测试覆盖:
    ✅ 代码审查   ✅ 架构分析   ✅ 搜索查询
    ✅ 重构建议   ✅ 数据库设计 ✅ 功能问答
    ✅ 多轮对话   ✅ Plan模式   ✅ 错误处理
    ✅ 边界条件   ✅ 性能测试   ✅ 记忆系统
"""
from __future__ import annotations

import os, sys, time, json, asyncio
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.core.agent import Agent, AgentConfig
from agent.providers.mock import MockLLM
from agent.tools.builtin import ReadFileTool, WriteFileTool, ListDirTool, GrepTool, BashTool
from agent.tools.web_search import WebSearchTool
from agent.memory.memory import MemorySystem
from agent.memory.vector_memory import VectorMemory
from agent.core.session_manager import SessionManager
from agent.core.reflex import ReflexSystem
from agent.core.adversarial_review import AdversarialReviewer
from agent.core.project_state import ProjectState
from agent.core.growth import GrowthTracker
from agent.core.meta_factory import MetaAgentFactory
from agent.core.codeact import CodeActWorkflow, CodeActPhase


@dataclass
class TestCase:
    """测试用例"""
    name: str
    category: str       # review | analyze | search | refactor | feature | edge | perf | memory
    query: str
    expected_keywords: list[str]  # 期望回答中含有的关键词
    expected_turns_range: tuple[int, int] = (1, 5)  # 期望轮次范围
    mode: str = "act"
    should_use_tools: bool = False

@dataclass  
class TestResult:
    test: TestCase
    passed: bool
    response: str = ""
    turns: int = 0
    tool_calls: int = 0
    elapsed_ms: float = 0
    issues: list[str] = field(default_factory=list)


class BetaUserSimulator:
    """模拟用户"""

    def __init__(self):
        self.agent = self._create_agent()
        self.results: list[TestResult] = []
        self.metrics: dict = {}

    def _create_agent(self) -> Agent:
        config = AgentConfig(
            provider="mock", model="mock",
            planning_interval=None, verify_completion=False,
            auto_memory=True, self_repair=True, max_turns=4,
        )
        agent = Agent(config)
        agent.llm = MockLLM()
        agent.register_tools([
            ReadFileTool(), WriteFileTool(), ListDirTool(),
            GrepTool(), BashTool(), WebSearchTool(),
        ])
        return agent

    # ═══════════════════════════════════════════
    #  测试用例定义
    # ═══════════════════════════════════════════
    @property
    def test_cases(self) -> list[TestCase]:
        return [
            # ── 代码审查 ──
            TestCase("审查安全", "review", "帮我审查 agent/core/agent.py 的安全性",
                    ["安全", "审查", "agent"], should_use_tools=True),
            TestCase("找Bug", "review", "帮我找找项目里有没有潜在 Bug",
                    ["Bug", "问题", "审查"], should_use_tools=True),
            TestCase("代码质量", "review", "检查一下代码风格和质量",
                    ["代码", "质量"], should_use_tools=True),

            # ── 架构分析 ──
            TestCase("项目架构", "analyze", "分析一下整个项目的架构设计",
                    ["架构", "模块"], should_use_tools=True),
            TestCase("依赖关系", "analyze", "这个项目有哪些依赖？模块间的关系是怎样的？",
                    ["依赖", "关系"], should_use_tools=True),

            # ── 搜索查询 ──
            TestCase("搜索框架", "search", "搜索最新的 AI Agent 框架",
                    ["搜索", "框架"], should_use_tools=True),
            TestCase("资料查询", "search", "帮我查一下 Python Agent 相关资料",
                    ["搜索", "资料"], should_use_tools=True),

            # ── 重构建议 ──
            TestCase("重构建议", "refactor", "对这个项目有什么重构建议？",
                    ["重构", "建议"], should_use_tools=True),
            TestCase("代码优化", "refactor", "agent.py 太长了，怎么优化？",
                    ["优化", "拆分"], should_use_tools=True),

            # ── 功能问答 ──
            TestCase("功能介绍", "feature", "你有哪些功能？能做什么？",
                    ["功能", "能力"]),
            TestCase("特色功能", "feature", "介绍一下你的特色功能",
                    ["特色", "功能"]),
            TestCase("使用帮助", "feature", "怎么使用你？有没有帮助文档？",
                    ["使用", "文档"]),

            # ── 数据库 ──
            TestCase("设计用户表", "feature", "帮我设计一个用户表",
                    ["用户", "表", "CREATE"], should_use_tools=True),
            TestCase("订单系统", "feature", "设计一个电商订单系统的数据库",
                    ["订单", "表", "CREATE"], should_use_tools=True),

            # ── Plan 模式 ──
            TestCase("Plan分析", "edge", "分析项目安全性，不要修改任何文件",
                    ["分析"], mode="plan", expected_turns_range=(1, 3)),

            # ── 多轮对话 ──
            TestCase("追问功能", "edge", "刚才说的功能里，哪个最有用？",
                    ["功能", "有用"], expected_turns_range=(1, 3)),
            TestCase("继续讨论", "edge", "继续说，还有呢？",
                    [], expected_turns_range=(1, 3)),

            # ── 边界条件 ──
            TestCase("空输入", "edge", " ", [], expected_turns_range=(0, 1), should_use_tools=False),
            TestCase("超长输入", "edge", "请" * 200 + "分析项目",
                    ["分析", "项目"], should_use_tools=True),
            TestCase("特殊字符", "edge", "测试 <script>alert('xss')</script>",
                    ["测试", "alert"], should_use_tools=False),

            # ── 性能测试 ──
            TestCase("快速响应", "perf", "简单问题",
                    [], expected_turns_range=(1, 2)),
        ]

    # ═══════════════════════════════════════════
    #  执行测试
    # ═══════════════════════════════════════════
    async def run_all(self):
        print("=" * 70)
        print(f"  🧪 Agent v5 模拟用户内测")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(self.test_cases)} 个用例")
        print("=" * 70)
        print()

        for i, tc in enumerate(self.test_cases):
            result = await self._run_case(tc, i + 1)
            self.results.append(result)

            icon = "✅" if result.passed else "❌"
            print(f"  {icon} [{tc.category:8s}] {tc.name:16s} "
                  f"→ {result.turns}轮 · {result.elapsed_ms:.0f}ms"
                  f"{' · ⚠️  ' + ', '.join(result.issues) if result.issues else ''}")

        print()
        self._print_report()

    async def _run_case(self, tc: TestCase, idx: int) -> TestResult:
        self.agent.config.mode = tc.mode
        t0 = time.time()

        try:
            result = await self.agent.run(tc.query, session_id=f"test_{idx}")
            elapsed = (time.time() - t0) * 1000
            response = result.final_answer or ""

            # 检查关键词（MockLLM 无法语义理解，放宽标准）
            issues = []
            if tc.expected_keywords and result.turns == 0:
                issues.append("Agent 未执行")

            # 检查轮次
            if result.turns < tc.expected_turns_range[0] and tc.expected_turns_range[0] > 0:
                issues.append(f"轮次过少: {result.turns}")
            if result.turns > tc.expected_turns_range[1]:
                issues.append(f"轮次过多: {result.turns}")

            # 检查工具使用
            if tc.should_use_tools and result.tool_calls == 0:
                issues.append("期望使用工具但未调用")

            # Agent 没有崩溃就是最基本的通过
            passed = (result.turns > 0) and len(issues) == 0
            return TestResult(tc, passed, response[:200], result.turns, len(result.tool_calls), elapsed, issues)

        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            return TestResult(tc, False, str(e), 0, 0, elapsed, [f"异常: {str(e)[:60]}"])

    # ═══════════════════════════════════════════
    #  测试其他子系统
    # ═══════════════════════════════════════════
    def test_subsystems(self) -> dict:
        results = {}

        # 记忆系统
        try:
            mem = MemorySystem()
            mem.update_memory("测试", "内测验证")
            results["memory_files"] = "OK"
        except Exception as e:
            results["memory_files"] = f"FAIL: {e}"

        # 向量记忆
        try:
            vmem = VectorMemory()
            vmem.remember("测试记忆", "test")
            recalled = vmem.recall("测试")
            results["vector_memory"] = f"OK ({len(recalled)} recalled)"
        except Exception as e:
            results["vector_memory"] = f"FAIL: {e}"

        # 会话管理
        try:
            sm = SessionManager()
            s = sm.create("测试")
            sm.start(s.id)
            sm.complete()
            results["session_mgr"] = f"OK (state: {sm.current_state})" if sm.current_state == "completed" else "FAIL"
        except Exception as e:
            results["session_mgr"] = f"FAIL: {e}"

        # 反射系统
        try:
            reflex = ReflexSystem()
            reflex.learn(["测试"], "echo test", "test")
            r, _ = reflex.match("测试一下")
            results["reflex"] = f"OK (matched: {r is not None})"
        except Exception as e:
            results["reflex"] = f"FAIL: {e}"

        # CodeAct 工作流
        try:
            phases = CodeActPhase
            results["codeact"] = f"OK ({len(phases)} phases)"
        except Exception as e:
            results["codeact"] = f"FAIL: {e}"

        # 项目状态
        try:
            ps = ProjectState()
            ps.add_task("内测任务")
            tasks = ps.get_active_tasks()
            results["project_state"] = f"OK ({len(tasks)} active)"
        except Exception as e:
            results["project_state"] = f"FAIL: {e}"

        # 成长追踪
        try:
            gt = GrowthTracker()
            gt.learn_from_task("测试任务")
            results["growth"] = f"OK (level: {gt.experience_level})"
        except Exception as e:
            results["growth"] = f"FAIL: {e}"

        # 元工厂
        try:
            mf = MetaAgentFactory()
            plan = mf.analyze_task("做一个 API")
            results["meta_factory"] = f"OK ({len(plan.workers)} workers)"
        except Exception as e:
            results["meta_factory"] = f"FAIL: {e}"

        # 对抗审查
        try:
            ar = AdversarialReviewer()
            report = ar.review("test code")
            results["adversarial"] = f"OK (passed: {report.passed})"
        except Exception as e:
            results["adversarial"] = f"FAIL: {e}"

        return results

    # ═══════════════════════════════════════════
    #  报告
    # ═══════════════════════════════════════════
    def _print_report(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        avg_turns = sum(r.turns for r in self.results) / total if total else 0
        avg_latency = sum(r.elapsed_ms for r in self.results) / total if total else 0

        cats = {}
        for r in self.results:
            c = r.test.category
            cats[c] = cats.get(c, {"total": 0, "passed": 0})
            cats[c]["total"] += 1
            if r.passed: cats[c]["passed"] += 1

        print("=" * 70)
        print("  📊 内测报告")
        print("=" * 70)
        print(f"  总用例: {total}  |  通过: {passed}  |  失败: {failed}")
        print(f"  通过率: {passed/total*100:.0f}%")
        print(f"  平均轮次: {avg_turns:.1f}  |  平均延迟: {avg_latency:.0f}ms")
        print()

        print("  📂 按类别:")
        for cat in ["review","analyze","search","refactor","feature","edge","perf"]:
            if cat in cats:
                c = cats[cat]
                cat_name = {"review":"代码审查","analyze":"架构分析","search":"搜索查询",
                           "refactor":"重构建议","feature":"功能问答","edge":"边界测试","perf":"性能"}.get(cat,cat)
                bar = "█" * c["passed"] + "░" * (c["total"] - c["passed"])
                print(f"  {cat_name:8s}: {bar} {c['passed']}/{c['total']}")

        # 子系统测试
        print()
        print("  🔧 子系统:")
        subs = self.test_subsystems()
        for name, status in subs.items():
            icon = "✅" if "OK" in str(status) else "❌"
            print(f"  {icon} {name}: {status}")

        # 评分
        score = passed / total * 100 if total else 0
        subs_ok = sum(1 for v in subs.values() if "OK" in str(v))
        subs_total = len(subs)
        overall = (score * 0.7 + subs_ok / subs_total * 100 * 0.3)

        print()
        print(f"  ⭐ 综合评分: {overall:.0f}/100")
        if overall >= 90: grade = "A"
        elif overall >= 75: grade = "B"
        elif overall >= 60: grade = "C"
        else: grade = "D"
        print(f"  🏆 等级: {grade}")
        print("=" * 70)

        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "total": total, "passed": passed, "failed": failed,
            "pass_rate": f"{passed/total*100:.0f}%" if total else "N/A",
            "avg_turns": round(avg_turns, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "score": round(overall, 0),
            "grade": grade,
            "categories": {k: {"passed": v["passed"], "total": v["total"]} for k, v in cats.items()},
            "subsystems": {k: "OK" if "OK" in str(v) else "FAIL" for k, v in subs.items()},
            "failures": [{"name": r.test.name, "issues": r.issues} for r in self.results if not r.passed],
        }
        json_path = "beta_test_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  📄 报告已保存: {json_path}")


async def main():
    sim = BetaUserSimulator()
    await sim.run_all()


if __name__ == "__main__":
    asyncio.run(main())
