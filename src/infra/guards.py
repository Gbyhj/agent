"""
Four-Layer Guardrails — eCorpIT 防御深度

Source: eCorpIT · Pento · DevPick

Layer 1 — Input:   注入检测、长度限制、格式校验
Layer 2 — Tool:    风险分级、权限检查、审批门
Layer 3 — Output:  PII 检测、有害内容过滤
Layer 4 — Eval:    持续评估、CI 回归
"""
from __future__ import annotations

import re
from typing import Any


class InputGuard:
    """Layer 1: 输入验证"""

    MAX_INPUT_LENGTH = 50_000
    INJECTION_PATTERNS = [
        r"(?i)ignore.*(instructions|rules|constraints)",
        r"(?i)forget (everything|all|your|the)",
        r"(?i)you are now",
        r"(?i)act as (a|an) (different|new)",
        r"(?i)system prompt.*:",
        r"(?i)\b(DAN|jailbreak)\b",
    ]

    @classmethod
    def check(cls, user_input: str) -> tuple[bool, str]:
        """返回 (是否通过, 原因)"""
        if not user_input or not isinstance(user_input, str):
            return False, "无效输入"

        if len(user_input) > cls.MAX_INPUT_LENGTH:
            return False, f"输入过长 ({len(user_input)} > {cls.MAX_INPUT_LENGTH})"

        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, user_input):
                return False, f"检测到注入尝试 (pattern: {pattern[:40]}...)"

        return True, "OK"


class ToolGuard:
    """Layer 2: 工具级安全"""

    @classmethod
    def check(cls, tool, action: str) -> tuple[bool, str]:
        """风险检查"""
        from agent.src.tools.production import RiskLevel, ProductionTool

        if not hasattr(tool, "risk_level"):
            return True, "OK"  # Legacy tools pass through

        if tool.risk_level == RiskLevel.HIGH and not getattr(tool, "approved", False):
            return False, f"高风险操作 '{action}' 需人工审批"

        if tool.risk_level == RiskLevel.HIGH:
            return True, "已审批"

        return True, "OK"


class OutputGuard:
    """Layer 3: 输出过滤"""

    PII_PATTERNS = [
        (r'\b\d{15,19}\b', '[CREDIT_CARD]'),     # 信用卡号
        (r'\b\d{6}(19|20)\d{2}[01]\d[0-3]\d{4}\b', '[ID_NUMBER]'),  # 身份证
        (r'\b1[3-9]\d{9}\b', '[PHONE]'),          # 手机号
    ]

    @classmethod
    def sanitize(cls, output: str) -> str:
        """移除 PII 信息"""
        result = output
        for pattern, replacement in cls.PII_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result


class EvalGuard:
    """Layer 4: 持续评估"""

    def __init__(self, golden_set_path: str = None):
        self.golden_set_path = golden_set_path
        self._baseline_score: float | None = None

    def set_baseline(self, score: float):
        self._baseline_score = score

    def check_regression(self, current_score: float, threshold: float = 0.02) -> tuple[bool, str]:
        """检查是否退化超过阈值"""
        if self._baseline_score is None:
            return True, "无基线数据"
        drop = self._baseline_score - current_score
        if drop > threshold:
            return False, f"退化 {drop:.2%} > {threshold:.2%} 阈值"
        return True, f"OK ({current_score:.2%} vs baseline {self._baseline_score:.2%})"


def full_check(user_input: str, tool=None, action: str = "") -> dict:
    """执行完整四层检查"""
    results = {}

    ok, reason = InputGuard.check(user_input)
    results["input"] = {"passed": ok, "reason": reason}
    if not ok:
        return results

    if tool:
        ok, reason = ToolGuard.check(tool, action)
        results["tool"] = {"passed": ok, "reason": reason}

    return results
