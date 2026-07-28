"""
CodeAct Iteration — OpenHands 精髓

OpenHands 的 CodeAct Agent 有五步标准流程:
  Explore → Analyze → Test → Implement → Verify

不是简单的 "提问→回答"，而是完整的工程迭代循环。

核心原则（来自 OpenHands 系统提示）:
1. 实现前先彻底探索代码库
2. 使用单个文件，不要创建多个版本
3. 对于全局替换用 sed，而不是多次打开文件编辑器
4. 永远不要为同一个文件创建多个版本
5. Bug 修复前先写测试复现
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class CodeActPhase(Enum):
    EXPLORE = "explore"       # 探索代码库
    ANALYZE = "analyze"       # 分析方案
    TEST_BEFORE = "test_before"  # 先写测试
    IMPLEMENT = "implement"   # 实施修改
    VERIFY = "verify"         # 验证结果


@dataclass
class CodeActStep:
    phase: CodeActPhase
    prompt: str
    tools: list[str]          # 该阶段可用的工具
    expected_output: str      # 期望产出


class CodeActWorkflow:
    """
    OpenHands CodeAct 标准工作流

    对应 OpenHands 系统提示中的五步流程:
    1. EXPLORE:    查找相关文件，理解上下文 (find, grep, read_file)
    2. ANALYZE:    考虑多种方案，选择最优 (think, read_file)
    3. TEST_BEFORE: Bug 修复前先写测试复现 (write_file, bash)
    4. IMPLEMENT:   最小化、针对性修改 (write_file, bash, sed)
    5. VERIFY:     运行测试，检查边缘情况 (bash, read_file)
    """

    WORKFLOW = [
        CodeActStep(
            phase=CodeActPhase.EXPLORE,
            prompt="""彻底探索相关文件，理解代码库上下文。

使用高效的工具，适当使用过滤器减少不必要操作:
- find/grep 查找相关文件
- read_file 读取关键文件
- 关注 import 和依赖关系

产出: 相关文件列表 + 代码结构理解""",
            tools=["read_file", "list_dir", "grep"],
            expected_output="理解了 N 个相关文件的结构和依赖",
        ),
        CodeActStep(
            phase=CodeActPhase.ANALYZE,
            prompt="""考虑多种实现方案，选择最有希望的一种。

不要急于写代码，先想清楚:
- 最少改动是什么？
- 会不会影响其他模块？
- 有没有更简单的方案？

产出: 选定的方案 + 理由""",
            tools=["read_file", "grep"],
            expected_output="选定了方案 X，因为...",
        ),
        CodeActStep(
            phase=CodeActPhase.TEST_BEFORE,
            prompt="""在实施修改之前，先编写测试来复现问题或验证预期行为。

OpenHands 原则:
- Bug 修复前先写测试复现 Bug
- 新功能前先写测试定义预期行为
- 测试应覆盖边缘情况

产出: 测试代码（能复现问题或定义预期）""",
            tools=["write_file", "bash", "read_file"],
            expected_output="测试已编写，可以复现当前行为",
        ),
        CodeActStep(
            phase=CodeActPhase.IMPLEMENT,
            prompt="""进行有针对性的、最小的更改。

OpenHands 原则:
- 直接编辑，不要创建不同文件名的新文件
- 全局替换用 sed，不要多次打开编辑器
- 永远不要为同一文件创建多个版本
- 使用单个文件，而不是多个版本

产出: 已修改的文件""",
            tools=["write_file", "bash"],
            expected_output="已实施最小化修改",
        ),
        CodeActStep(
            phase=CodeActPhase.VERIFY,
            prompt="""验证实现是否正确。

- 运行之前编写的测试
- 检查边缘情况
- 确认没有引入新问题
- 如果测试失败，回到 IMPLEMENT 修改

产出: 验证报告（通过/需修改）""",
            tools=["bash", "read_file", "grep"],
            expected_output="✅ 所有测试通过 / ❌ 需要修改...",
        ),
    ]

    @classmethod
    def get_phase_prompt(cls, phase: CodeActPhase) -> str:
        for step in cls.WORKFLOW:
            if step.phase == phase:
                return step.prompt
        return ""

    @classmethod
    def get_phase_tools(cls, phase: CodeActPhase) -> list[str]:
        for step in cls.WORKFLOW:
            if step.phase == phase:
                return step.tools
        return []

    @classmethod
    def describe(cls) -> str:
        lines = ["# CodeAct 工作流 (OpenHands)", ""]
        for i, step in enumerate(cls.WORKFLOW, 1):
            lines.append(f"## Phase {i}: {step.phase.value.upper()}")
            lines.append(f"工具: {', '.join(step.tools)}")
            lines.append(f"期望: {step.expected_output}")
            lines.append("")
        return "\n".join(lines)
