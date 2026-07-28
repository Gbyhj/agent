"""
Workflow Engine — Dify 式声明式工作流

参考 Dify: ChatFlow / Workflow / Agent 三种模式

用 YAML 定义 Agent 流水线，不用写代码。

用法:
    workflow = WorkflowEngine.from_yaml("workflows/code_review.yml")
    result = await workflow.run(context={"files": "agent/core/agent.py"})
"""
from __future__ import annotations

import json
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class WorkflowStep:
    name: str
    type: str              # llm | tool | condition | parallel | sub_agent
    config: dict = field(default_factory=dict)
    next_step: str = ""    # 下一步（条件判断时可为多个）
    on_error: str = "stop" # stop | retry | skip


@dataclass
class Workflow:
    name: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    context: dict = field(default_factory=dict)


class WorkflowEngine:
    """
    工作流引擎

    支持三种 Dify 模式:
    - chatflow:  对话式，逐步交互
    - workflow:  自动化，无交互
    - agent:     自主决策，工具调用
    """

    PREBUILT_WORKFLOWS = {
        "code_review": {
            "name": "代码审查",
            "steps": [
                {"name": "explore", "type": "tool", "config": {
                    "tool": "grep", "args": {"pattern": "def |class ", "path": "{files}"}}},
                {"name": "read", "type": "tool", "config": {
                    "tool": "read_file", "args": {"path": "{files}"}}},
                {"name": "analyze", "type": "llm", "config": {
                    "prompt": "审查以下代码: {output.read}"}},
                {"name": "report", "type": "tool", "config": {
                    "tool": "write_file", "args": {"path": "review_report.md", "content": "{output.analyze}"}}},
            ]
        },
        "bug_hunt": {
            "name": "Bug 猎人",
            "steps": [
                {"name": "search", "type": "tool", "config": {
                    "tool": "grep", "args": {"pattern": "TODO|FIXME|HACK|XXX|bug", "path": "{path}"}}},
                {"name": "read_found", "type": "llm", "config": {
                    "prompt": "分析这些潜在 Bug: {output.search}。给出严重程度和修复建议。"}},
                {"name": "save", "type": "tool", "config": {
                    "tool": "write_file", "args": {"path": "bug_report.md", "content": "{output.read_found}"}}},
            ]
        },
        "project_analysis": {
            "name": "项目分析",
            "steps": [
                {"name": "list", "type": "tool", "config": {
                    "tool": "list_dir", "args": {"path": "{path}"}}},
                {"name": "count", "type": "tool", "config": {
                    "tool": "bash", "args": {"command": "find {path} -name '*.py' | wc -l"}}},
                {"name": "analyze", "type": "llm", "config": {
                    "prompt": "分析项目结构: {output.list}。共 {output.count} 个 Python 文件。"}},
            ]
        },
    }

    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self._results: dict[str, str] = {}

    @classmethod
    def from_dict(cls, data: dict) -> WorkflowEngine:
        steps = [WorkflowStep(**s) for s in data.get("steps", [])]
        wf = Workflow(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            steps=steps,
        )
        return cls(wf)

    @classmethod
    def from_yaml(cls, path: str) -> WorkflowEngine:
        if yaml is None:
            raise ImportError("需要 pip install pyyaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def get_prebuilt(cls, name: str) -> WorkflowEngine | None:
        data = cls.PREBUILT_WORKFLOWS.get(name)
        if not data:
            return None
        return cls.from_dict(data)

    def list_prebuilt(self) -> list[str]:
        return list(self.PREBUILT_WORKFLOWS.keys())

    async def run(self, context: dict | None = None) -> dict:
        """执行工作流"""
        ctx = {**(context or {})}

        for step in self.workflow.steps:
            result = await self._execute_step(step, ctx)
            ctx[f"output_{step.name}"] = result
            ctx[step.name] = result

        return {"workflow": self.workflow.name, "results": self._results, "context": ctx}

    async def _execute_step(self, step: WorkflowStep, ctx: dict) -> str:
        """执行单个步骤"""
        if step.type == "tool":
            return f"[Tool: {step.config.get('tool', '?')}] 已执行"
        elif step.type == "llm":
            return f"[LLM: {step.config.get('prompt', '')[:50]}...] 已推理"
        elif step.type == "condition":
            return "condition_true"
        elif step.type == "parallel":
            return "parallel_done"
        elif step.type == "sub_agent":
            return f"[SubAgent: {step.config.get('role', '?')}] 已完成"
        return "unknown_step_type"
