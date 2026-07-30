"""
LLM-as-Judge — 用 DeepSeek 做裁判评估 Agent 输出

比 keyword 匹配更准确，能理解语义、上下文和代码质量。
"""
from __future__ import annotations

import json, time
from typing import Any


class LLMJudge:
    """用 LLM 做裁判评分"""

    JUDGE_PROMPT = """你是一个专业的 AI Agent 评估裁判。请评估以下 Agent 的回答质量。

任务: {task}
期望关键词: {keywords}

Agent 回答:
{answer}

请从以下四个维度评分 (每个维度 0-25 分，满分 100):
1. 相关性 (0-25): 回答是否直接针对任务？
2. 完整性 (0-25): 是否覆盖了所有要求？
3. 准确性 (0-25): 信息是否正确、没有幻觉？
4. 可操作性 (0-25): 是否给出可执行的建议？

请只返回 JSON 格式:
{{"relevance": <0-25>, "completeness": <0-25>, "accuracy": <0-25>, "actionability": <0-25>, "total": <0-100>, "brief": "<一句话评价>"}}"""

    def __init__(self, llm=None):
        self.llm = llm
        self._cache: dict = {}

    def score(self, task: str, answer: str, keywords: list[str] = None) -> dict:
        """对回答评分 (0-100)"""
        cache_key = task[:50] + str(answer)[:50]
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 快速本地评分 (无 LLM 时)
        if not self.llm:
            return self._local_score(task, answer, keywords or [])

        try:
            prompt = self.JUDGE_PROMPT.format(
                task=task, keywords=", ".join(keywords or []), answer=answer[:2000],
            )
            resp = self.llm.chat([{"role": "user", "content": prompt}])
            # 提取 JSON
            text = resp.content if hasattr(resp, 'content') else str(resp)
            if "{" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                result = json.loads(text[start:end])
            else:
                result = {"total": 50, "brief": "无法解析"}
        except Exception:
            result = self._local_score(task, answer, keywords or [])

        self._cache[cache_key] = result
        return result

    def _local_score(self, task: str, answer: str, keywords: list[str]) -> dict:
        """快速本地评分 (退路)"""
        aw = answer.lower()
        tw = set(task.lower().split())
        aw_set = set(aw.split())

        relevance = min(len(tw & aw_set) / max(len(tw), 1) * 25, 25)
        completeness = sum(1 for kw in keywords if kw.lower() in aw) / max(len(keywords), 1) * 25
        accuracy = 20  # default
        actionability = min(len(answer) / 200 * 25, 25)
        total = relevance + completeness + accuracy + actionability
        return {
            "relevance": round(relevance, 1), "completeness": round(completeness, 1),
            "accuracy": round(accuracy, 1), "actionability": round(actionability, 1),
            "total": round(total, 1), "brief": f"本地评分"
        }

    def batch_score(self, cases: list[dict]) -> dict:
        """批量评分"""
        results = []
        total = 0
        for case in cases:
            s = self.score(case["task"], case.get("answer", ""), case.get("keywords", []))
            results.append({**case, "score": s})
            total += s.get("total", 0)

        avg = total / max(len(cases), 1)
        return {"average": round(avg, 1), "results": results, "grade": self._grade(avg)}

    def _grade(self, score: float) -> str:
        if score >= 80: return "A"
        if score >= 60: return "B"
        if score >= 40: return "C"
        return "D"
