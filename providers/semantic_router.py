"""
Semantic Router — LiteLLM 语义难度路由

参考 LiteLLM complexity router:
先让便宜模型(Flash)分析任务复杂度，再决定用哪个模型。

流程:
    task → Flash分析("这个任务复杂吗? 1-10") → 
    1-3: Flash · 4-6: Flash大窗口 · 7-10: Pro

比关键词匹配更准确，单次分析成本 ~¥0.0001。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComplexityScore:
    score: int           # 1-10
    reason: str          # 为什么是这个分数
    suggested_model: str # flash / pro / coder


class SemanticRouter:
    """语义难度路由"""

    COMPLEXITY_PROMPT = """分析以下任务的复杂度，给出1-10分。

评分标准:
1-3: 简单 (读文件、列目录、简单问答)
4-6: 中等 (搜索、分析、代码审查)
7-10: 复杂 (重构、架构设计、多文件修改)

只回复JSON: {"score": N, "reason": "简短中文原因"}"""

    def __init__(self, llm=None):
        self._llm = llm

    def analyze(self, task: str) -> ComplexityScore:
        """分析任务复杂度"""
        # 先用规则快速判断
        quick = self._quick_check(task)
        if quick is not None:
            return quick

        # 需要 LLM 就调用
        if self._llm:
            try:
                resp = self._llm.chat([
                    {"role": "system", "content": self.COMPLEXITY_PROMPT},
                    {"role": "user", "content": task[:500]},
                ])
                import json
                data = json.loads(resp.content or "{}")
                score = int(data.get("score", 5))
                return ComplexityScore(
                    score=score,
                    reason=data.get("reason", "LLM 分析"),
                    suggested_model=self._model_for(score),
                )
            except Exception:
                pass

        # Fallback: 规则
        return self._quick_check(task) or ComplexityScore(5, "默认", "flash")

    def _quick_check(self, task: str) -> ComplexityScore | None:
        """规则快速判断"""
        t = task.lower()

        # 复杂关键词
        complex_kw = ["重构", "架构", "设计模式", "大规模", "迁移", "重写",
                       "refactor", "architecture", "redesign"]
        if any(kw in t for kw in complex_kw):
            return ComplexityScore(8, "包含复杂关键词", "pro")

        # 代码生成 (放在中等之前，优先匹配)
        code_kw = ["写代码", "生成代码", "实现功能", "编写函数",
                    "创建新的", "写一个", "生成一个"]
        if any(kw in t for kw in code_kw):
            return ComplexityScore(4, "代码生成任务", "coder")

        # 中等关键词
        medium_kw = ["分析", "审查", "检测", "搜索", "优化", "测试",
                      "analyze", "review", "search", "optimize", "test"]
        if any(kw in t for kw in medium_kw):
            return ComplexityScore(5, "包含中等关键词", "flash")

        # 简单任务
        if len(task) < 20:
            return ComplexityScore(2, "简短任务", "flash")

        # 代码生成 (放在最后,避免误匹配)
        code_kw = ["写代码", "生成代码", "实现功能", "编写函数",
                    "write code", "create function", "generate code"]
        if any(kw in t for kw in code_kw):
            return ComplexityScore(4, "代码生成任务", "coder")

        return None

    def _model_for(self, score: int) -> str:
        if score <= 3:
            return "flash"
        elif score <= 6:
            return "flash"
        else:
            return "pro"

    def route(self, task: str) -> str:
        """路由: 返回应该用的模型名"""
        return self.analyze(task).suggested_model
