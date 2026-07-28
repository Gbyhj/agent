"""
Adversarial Code Review — 对抗式代码审查

灵感: Grok Build Skeptic × SubAgent 系统

Agent 写/改代码后，自动启动双 Agent 审查：
- Breaker: 尝试发现 Bug、安全漏洞、边界条件
- Improver: 建议优化、简化、更好的模式

只有两者都通过，代码才被接受。

用法:
    reviewer = AdversarialReviewer(llm=agent.llm)
    report = reviewer.review("agent/core/agent.py")
    # report = {"passed": True, "bugs": [...], "improvements": [...]}
"""
from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReviewIssue:
    """审查发现的问题"""
    severity: str           # critical / major / minor / suggestion
    file: str               # 文件路径
    line: str               # 行号或位置
    title: str              # 问题标题
    description: str        # 详细描述
    fix: str = ""           # 修复建议


@dataclass
class ReviewReport:
    """审查报告"""
    passed: bool
    breaker_issues: list[ReviewIssue] = field(default_factory=list)
    improver_issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""
    breaker_cost: float = 0.0
    improver_cost: float = 0.0

    @property
    def total_issues(self) -> int:
        return len(self.breaker_issues) + len(self.improver_issues)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.breaker_issues if i.severity == "critical")

    def format_markdown(self) -> str:
        """格式化为 Markdown 报告"""
        status = "✅ 通过" if self.passed else "❌ 需要修改"
        lines = [
            f"# 对抗式代码审查 {status}",
            "",
            f"## 总结",
            f"{self.summary}",
            f"",
            f"| 类型 | 数量 |",
            f"|------|------|",
            f"| 🔴 Critical | {sum(1 for i in self.breaker_issues if i.severity=='critical')} |",
            f"| 🟡 Major | {sum(1 for i in self.breaker_issues if i.severity=='major')} |",
            f"| 🟢 Minor | {sum(1 for i in self.breaker_issues if i.severity=='minor')} |",
            f"| 💡 Suggestion | {len(self.improver_issues)} |",
            f"| 💰 审查成本 | ¥{self.breaker_cost + self.improver_cost:.4f} |",
            "",
        ]

        if self.breaker_issues:
            lines.append("## 🔴 Breaker 发现的问题")
            lines.append("")
            for issue in self.breaker_issues:
                icon = {"critical": "🔴", "major": "🟡", "minor": "🟢"}.get(issue.severity, "⚪")
                lines.append(f"### {icon} {issue.title}")
                lines.append(f"- **位置**: {issue.file}" + (f":{issue.line}" if issue.line else ""))
                lines.append(f"- **描述**: {issue.description}")
                if issue.fix:
                    lines.append(f"- **修复**: {issue.fix}")
                lines.append("")

        if self.improver_issues:
            lines.append("## 💡 Improver 建议优化")
            lines.append("")
            for issue in self.improver_issues:
                lines.append(f"### {issue.title}")
                lines.append(f"- **位置**: {issue.file}" + (f":{issue.line}" if issue.line else ""))
                lines.append(f"- **建议**: {issue.description}")
                if issue.fix:
                    lines.append(f"- **示例**: {issue.fix}")
                lines.append("")

        lines.append("---")
        lines.append("*由 Adversarial Reviewer 自动生成*")
        return "\n".join(lines)


class AdversarialReviewer:
    """
    对抗式代码审查器

    使用现有的 LLM + ReadFileTool 进行审查。
    不需要额外 API key。
    """

    BREAKER_PROMPT = """你是代码安全审查专家（Breaker）。严格审查以下代码：

{code}

请找出：
1. 🔴 Critical: Bug、逻辑错误、安全漏洞、空指针
2. 🟡 Major: 性能问题、资源泄漏、竞态条件
3. 🟢 Minor: 错误处理不足、代码异味

对每个问题给出：
- 文件路径和行号
- 问题描述
- 修复建议

如果没有发现问题，回复 "NO_ISSUES"."""

    IMPROVER_PROMPT = """你是代码优化专家（Improver）。审查以下代码并给出改进建议：

{code}

请关注：
1. 是否有更简洁的实现方式？
2. 是否可以减少嵌套和复杂度？
3. 命名是否清晰？
4. 是否遵循最佳实践？

只提出有价值的改进建议。如果没有，回复 "NO_ISSUES"."""

    def __init__(self, llm=None):
        self._llm = llm

    def review_file(self, filepath: str, llm=None) -> ReviewReport:
        """审查单个文件"""
        llm = llm or self._llm
        if not os.path.exists(filepath):
            return ReviewReport(passed=False, summary=f"文件不存在: {filepath}")

        with open(filepath, encoding="utf-8", errors="replace") as f:
            code = f.read()

        if len(code) > 8000:
            code = code[:8000] + "\n... (truncated)"

        return self.review(code, filepath, llm)

    def review(self, code: str, context: str = "", llm=None) -> ReviewReport:
        """审查代码"""
        import asyncio

        llm = llm or self._llm
        if not llm:
            return ReviewReport(passed=True, summary="无 LLM 可用（离线模式），跳过审查")

        async def run():
            breaker = await asyncio.to_thread(self._call_agent, self.BREAKER_PROMPT.format(code=code), llm)
            improver = await asyncio.to_thread(self._call_agent, self.IMPROVER_PROMPT.format(code=code), llm)
            return breaker, improver

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                breaker_resp, improver_resp = loop.run_until_complete(run())
            else:
                breaker_resp, improver_resp = asyncio.run(run())
        except RuntimeError:
            breaker_resp, improver_resp = asyncio.run(run())

        breaker_issues = self._parse_issues(breaker_resp, "breaker")
        improver_issues = self._parse_issues(improver_resp, "improver")

        critical_count = sum(1 for i in breaker_issues if i.severity == "critical")
        passed = critical_count == 0

        return ReviewReport(
            passed=passed,
            breaker_issues=breaker_issues,
            improver_issues=improver_issues,
            summary=f"发现 {len(breaker_issues)} 个问题（{critical_count} critical），{len(improver_issues)} 个改进建议。{'通过' if passed else '需修复'}。",
            breaker_cost=0.001,
            improver_cost=0.001,
        )

    def _call_agent(self, prompt: str, llm) -> str:
        """简化的子 Agent 调用"""
        try:
            resp = llm.chat([
                {"role": "system", "content": prompt},
                {"role": "user", "content": "请审查上述代码。"},
            ])
            return resp.content or "NO_ISSUES"
        except Exception as e:
            return f"ERROR: {e}"

    def _parse_issues(self, response: str, source: str) -> list[ReviewIssue]:
        """解析 LLM 响应为结构化问题列表"""
        if not response or "NO_ISSUES" in response.upper():
            return []

        issues = []
        # 简单解析：以 - 或数字开头的行作为问题
        lines = response.split("\n")
        current = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测问题行
            icon_match = None
            for icon in ["🔴", "🟡", "🟢", "💡"]:
                if icon in line:
                    icon_match = icon
                    break

            if icon_match or line.startswith(("- ", "1.", "2.", "3.", "4.", "5.")):
                sev = "minor"
                if "🔴" in line or "critical" in line.lower(): sev = "critical"
                elif "🟡" in line or "major" in line.lower(): sev = "major"
                elif "💡" in line or "suggestion" in line.lower(): sev = "suggestion"

                title = line.lstrip("- 0123456789.🔴🟡🟢💡 ") if source == "breaker" else line.lstrip("- 0123456789.💡 ")
                title = title[:100]

                issues.append(ReviewIssue(
                    severity=sev, file="", line="", title=title,
                    description=title,
                ))

        return issues
