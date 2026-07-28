"""
Tool Five Elements — SensusSoft 生产标准

每个工具都像公共 API 一样完善:
  1. JSON Schema 严格输入 (Pydantic)
  2. Idempotency Key (防重复)
  3. Risk Rating (low/medium/high)
  4. Structured Error Response
  5. Version History + Migration
"""
from __future__ import annotations

import uuid
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    LOW = "low"        # 读文件、搜索 → 自动执行
    MEDIUM = "medium"  # 写文件、生成 → 确认
    HIGH = "high"      # 执行命令、发送 → 审批


@dataclass
class ToolResult:
    """结构化工具结果"""
    success: bool
    data: Any = None
    error_code: str | None = None
    error_message: str | None = None

    @classmethod
    def ok(cls, data: Any) -> ToolResult:
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, code: str, message: str) -> ToolResult:
        return cls(success=False, error_code=code, error_message=message)


class ProductionTool:
    """生产级工具基类"""

    name: str = "base_tool"
    version: str = "1.0.0"
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_approval: bool = False

    def __init__(self):
        self._idempotency_keys: set = set()
        self._version_migrations: dict[str, callable] = {}

    def execute(self, **kwargs) -> ToolResult:
        """带 idempotency 保护的执行"""
        # Generate idempotency key
        args_hash = hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:12]
        idemp_key = f"{self.name}:{args_hash}"

        # Check already executed
        if idemp_key in self._idempotency_keys:
            return ToolResult.ok({"cached": True, "note": "Already executed"})

        # Execute
        try:
            result = self._execute(**kwargs)
            self._idempotency_keys.add(idemp_key)
            return ToolResult.ok(result)
        except Exception as e:
            return ToolResult.fail(
                code=type(e).__name__,
                message=str(e)[:200],
            )

    def _execute(self, **kwargs) -> Any:
        """子类实现具体逻辑"""
        raise NotImplementedError

    def needs_approval(self) -> bool:
        """高风险管理需要审批"""
        return self.risk_level == RiskLevel.HIGH or self.requires_approval

    def check_access(self, user_role: str) -> bool:
        """按角色检查权限"""
        if self.risk_level == RiskLevel.LOW:
            return True
        if self.risk_level == RiskLevel.MEDIUM and user_role in ("admin", "developer"):
            return True
        return user_role == "admin"
