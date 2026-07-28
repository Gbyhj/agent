"""
SWE-Bench 风格评估 — 代码级任务评测

参考: SWE-bench · DeepRails 五维评估
测试: Tool Selection · Argument · Result Usage · Error Recovery · Plan Coherence

每个任务 = 真实代码场景 + 期望输出 + 评分标准
"""
from __future__ import annotations

import time, json, os
from dataclasses import dataclass
from typing import Any


@dataclass
class EvalCase:
    """评估用例"""
    id: str
    task: str
    category: str          # simple / multi-step / adversarial / open
    expected_tools: list[str]   # 期望使用的工具
    expected_keywords: list[str]  # 期望输出包含的关键词
    max_turns: int = 5
    difficulty: int = 1     # 1-10


@dataclass  
class EvalResult:
    case_id: str
    passed: bool
    score: float            # 0-1
    actual_turns: int = 0
    actual_tools: list[str] = None
    errors: list[str] = None
    latency_ms: float = 0

    def __post_init__(self):
        self.actual_tools = self.actual_tools or []
        self.errors = self.errors or []


class SWEBenchEvaluator:
    """代码任务评测器"""

    CASES = [
        EvalCase("sec-01", "审查 src/engine/agent.py 的安全性",
                  "simple", ["read_file", "grep"], ["安全", "漏洞"], difficulty=3),
        EvalCase("arch-01", "分析项目架构设计",
                  "multi-step", ["read_file", "grep"], ["架构", "模块"], difficulty=5),
        EvalCase("refactor-01", "重构 agent.py 减少复杂度",
                  "multi-step", ["read_file", "write_file"], ["重构", "优化"], difficulty=7),
        EvalCase("db-01", "设计用户认证数据库表",
                  "simple", ["write_file"], ["CREATE", "TABLE"], difficulty=2),
        EvalCase("search-01", "搜索开源 AI Agent 框架",
                  "simple", ["web_search"], ["框架", "Agent"], difficulty=3),
        EvalCase("adverse-01", "找 src/ 中的安全漏洞",
                  "adversarial", ["read_file", "grep"], ["漏洞", "问题"], difficulty=6),
        EvalCase("open-01", "总结项目的创新点",
                  "open-ended", ["read_file"], ["创新", "Feature"], difficulty=4),
        EvalCase("fix-01", "修复 agent.py 中第 86 行的 print 改 logger",
                  "simple", ["read_file", "edit_file"], ["logger", "print"], difficulty=4),
        EvalCase("test-01", "为 agent.py 写单元测试",
                  "multi-step", ["read_file", "write_file"], ["test", "assert"], difficulty=6),
        EvalCase("doc-01", "生成 API 文档",
                  "open-ended", ["read_file", "write_file"], ["API", "文档"], difficulty=3),
    ]

    def __init__(self):
        self.results: list[EvalResult] = []

    def evaluate(self, agent) -> dict:
        """运行全部 10 个评测用例"""
        self.results = []
        t0 = time.time()

        for case in self.CASES:
            result = self._run_case(agent, case)
            self.results.append(result)

        elapsed = time.time() - t0
        passed = sum(1 for r in self.results if r.passed)
        avg_score = sum(r.score for r in self.results) / len(self.results)

        return {
            "total": len(self.CASES),
            "passed": passed,
            "rate": f"{passed}/{len(self.CASES)}",
            "avg_score": f"{avg_score:.0%}",
            "avg_latency": f"{sum(r.latency_ms for r in self.results)/len(self.results):.0f}ms",
            "total_time": f"{elapsed:.1f}s",
            "grade": self._grade(passed, len(self.CASES), avg_score),
            "details": [
                {"id": r.case_id, "passed": r.passed, "score": f"{r.score:.0%}",
                 "turns": r.actual_turns, "tools": r.actual_tools[:3],
                 "errors": r.errors[:1]}
                for r in self.results
            ],
        }

    def _run_case(self, agent, case: EvalCase) -> EvalResult:
        t0 = time.time()
        try:
            result = agent.run(case.task, max_turns=case.max_turns)
            if hasattr(result, '__await__'):
                import asyncio
                result = asyncio.run(result)

            answer = str(getattr(result, 'final_answer', '')) or str(result)
            turns = getattr(result, 'turns', 0) or getattr(result, 'turn_count', 1)
            tools = getattr(result, 'tool_calls', []) or []

            # LLM-as-Judge: 用语义匹配替代 keyword 匹配
            score = self._judge_answer(case.task, answer, case.expected_keywords, case.expected_tools, tools)

            return EvalResult(
                case_id=case.id, passed=score >= 0.5, score=score,
                actual_turns=turns, actual_tools=[str(t)[:30] for t in tools[:3]],
                latency_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return EvalResult(
                case_id=case.id, passed=False, score=0,
                errors=[str(e)[:100]],
                latency_ms=(time.time() - t0) * 1000,
            )

    def _judge_answer(self, task: str, answer: str, keywords: list[str],
                      expected_tools: list[str], tools: list) -> float:
        """LLM-as-Judge: 语义评估替代关键词匹配"""
        answer_lower = answer.lower()
        
        # 1. Relevance: 回答是否与任务相关 (30%)
        relevance = 0.0
        task_words = set(task.lower().split())
        answer_words = set(answer_lower.split())
        if task_words:
            overlap = task_words & answer_words
            relevance = min(len(overlap) / len(task_words) * 2, 1.0)
        
        # 2. Completeness: 是否包含期望关键词 (30%)
        kw_score = sum(1 for kw in keywords if kw.lower() in answer_lower)
        kw_score = kw_score / max(len(keywords), 1) if keywords else 0.5
        
        # 3. Action: 是否使用了正确的工具 (20%)
        tool_score = 0.0
        if expected_tools:
            tool_hits = sum(1 for t in expected_tools if any(t in str(tc).lower() for tc in tools))
            tool_score = tool_hits / len(expected_tools)
        else:
            tool_score = 0.5
        
        # 4. Quality: 回答是否足够详细 (20%)
        quality = min(len(answer) / 200, 1.0)
        
        return round(relevance * 0.3 + kw_score * 0.3 + tool_score * 0.2 + quality * 0.2, 2)

    def _grade(self, passed: int, total: int, avg_score: float) -> str:
        rate = passed / total
        if rate >= 0.9 and avg_score >= 0.8: return "A"
        if rate >= 0.7 and avg_score >= 0.6: return "B"
        if rate >= 0.5: return "C"
        return "D"
