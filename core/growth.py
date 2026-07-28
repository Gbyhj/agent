"""
Growing Personal AI — 成长型个人 AI

灵感: Mem0 自动提取 × OpenClaw SOUL.md × ChromaDB 语义记忆

三个维度自动进化:
1. 代码风格 — 缩进、命名、OOP/FP 偏好
2. 项目知识 — 架构、技术栈、关键决策
3. 工作习惯 — 常用命令、review 标准、时间模式

数据存储: ~/.agent_growth.json
"""
from __future__ import annotations

import os
import json
import re
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class StyleProfile:
    """代码风格画像"""
    indent: str = "4 spaces"
    naming: str = "snake_case"
    paradigm: str = "class-based"
    max_line_length: int = 120
    docstrings: bool = True
    type_hints: bool = True
    test_framework: str = "pytest"
    confidence: float = 0.0


@dataclass
class ProjectKnowledge:
    """项目知识"""
    language: str = "Python"
    frameworks: list[str] = field(default_factory=list)
    key_files: list[str] = field(default_factory=list)
    recent_decisions: list[dict] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class WorkHabits:
    """工作习惯"""
    peak_hours: list[int] = field(default_factory=lambda: [9, 10, 14, 15])
    common_commands: list[dict] = field(default_factory=list)
    review_style: str = "comprehensive"  # quick / normal / comprehensive
    prefers_plan_first: bool = True


class GrowthTracker:
    """
    成长追踪器

    不是一次性设置，而是日积月累自动学习。

    Day 1:  只知道你在用 Python
    Day 7:  了解你的代码风格
    Day 30: 能预测你下一步要做什么
    Day 90: 比你更了解你的项目
    """

    def __init__(self, path: str | None = None):
        self.path = path or os.path.expanduser("~/.agent_growth.json")
        self.style = StyleProfile()
        self.project = ProjectKnowledge()
        self.habits = WorkHabits()
        self._sessions: list[dict] = []
        self._total_tasks: int = 0
        self._first_seen: str = datetime.now().isoformat()
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                data = json.load(open(self.path, encoding="utf-8"))
                self.style = StyleProfile(**data.get("style", {}))
                self.project = ProjectKnowledge(**data.get("project", {}))
                self.habits = WorkHabits(**data.get("habits", {}))
                self._sessions = data.get("sessions", [])
                self._total_tasks = data.get("total_tasks", 0)
                self._first_seen = data.get("first_seen", self._first_seen)
            except Exception:
                pass

    def _save(self):
        data = {
            "style": self.style.__dict__,
            "project": self.project.__dict__,
            "habits": self.habits.__dict__,
            "sessions": self._sessions[-100:],
            "total_tasks": self._total_tasks,
            "first_seen": self._first_seen,
        }
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def learn_from_task(self, task: str, code_changes: list[str] | None = None):
        """从一次任务中学习"""
        self._total_tasks += 1

        # 学习代码风格
        if code_changes:
            self._learn_style(code_changes)

        # 学习项目知识
        self._learn_project(task)

        # 学习工作习惯
        self._learn_habits(task)

        self._sessions.append({
            "time": datetime.now().isoformat(),
            "task": task[:100],
            "day": self.days_active,
        })
        self._save()

    def _learn_style(self, changes: list[str]):
        """从代码变更中学习风格"""
        content = "\n".join(changes)

        # 缩进检测
        if "\t" in content:
            self.style.indent = "tabs"
        if "    " in content:
            self.style.indent = "4 spaces"
        if "  " in content and "    " not in content:
            self.style.indent = "2 spaces"

        # 命名检测
        if re.search(r"\bdef [a-z_]+", content):
            self.style.naming = "snake_case"
        if re.search(r"\bdef [A-Z][a-z]+", content):
            self.style.naming = "camelCase"

        # 范式检测
        if re.search(r"class \w+", content):
            self.style.paradigm = "class-based"
        if re.search(r"lambda|def \w+.*:.*\breturn\b", content):
            self.style.paradigm = "functional"

        # type hints
        self.style.type_hints = "->" in content or ": str" in content

        # 置信度随任务数增长
        self.style.confidence = min(1.0, self._total_tasks / 20)

    def _learn_project(self, task: str):
        """学习项目信息"""
        # 检测框架
        framework_signals = {
            "flask": ["flask", "Flask", "app.route"],
            "fastapi": ["fastapi", "FastAPI", "APIRouter"],
            "django": ["django", "Django", "urlpatterns"],
            "pytest": ["pytest", "conftest", "fixture"],
        }
        for fw, keywords in framework_signals.items():
            if any(kw.lower() in task.lower() for kw in keywords):
                if fw not in self.project.frameworks:
                    self.project.frameworks.append(fw)

        # 检测依赖
        deps = re.findall(r'(?:import|from)\s+(\w+)', task)
        for d in deps:
            if d not in self.project.dependencies and not d.startswith("_"):
                self.project.dependencies.append(d)

        self.project.dependencies = self.project.dependencies[-30:]

    def _learn_habits(self, task: str):
        """学习工作习惯"""
        hour = datetime.now().hour
        if hour not in self.habits.peak_hours:
            self.habits.peak_hours.append(hour)
            self.habits.peak_hours.sort()

        # 常用命令
        cmd_patterns = {
            "git": [r"\bgit\b"],
            "pytest": [r"\bpytest\b"],
            "docker": [r"\bdocker\b"],
            "grep": [r"\bgrep\b"],
            "sed": [r"\bsed\b"],
        }
        for cmd, patterns in cmd_patterns.items():
            if any(re.search(p, task, re.IGNORECASE) for p in patterns):
                existing = next((c for c in self.habits.common_commands if c["name"] == cmd), None)
                if existing:
                    existing["count"] += 1
                else:
                    self.habits.common_commands.append({"name": cmd, "count": 1})

        self.habits.common_commands.sort(key=lambda x: x["count"], reverse=True)
        self.habits.common_commands = self.habits.common_commands[:15]

        # Plan first 偏好
        if any(kw in task for kw in ["分析", "先看看", "审查", "review"]):
            self.habits.prefers_plan_first = True

    @property
    def days_active(self) -> int:
        first = datetime.fromisoformat(self._first_seen.split("T")[0])
        return (datetime.now() - first).days + 1

    @property
    def experience_level(self) -> str:
        if self._total_tasks < 5: return "新手 (Day 1-5)"
        if self._total_tasks < 20: return "熟练 (Day 6-20)"
        if self._total_tasks < 50: return "精通 (Day 21-50)"
        return f"专家 (Day {self.days_active})"

    @property
    def identity_summary(self) -> str:
        """生成身份摘要 — 注入 SOUL.md"""
        return f"""## Growth Profile
- **认识天数**: {self.days_active} 天
- **完成任务**: {self._total_tasks}
- **经验等级**: {self.experience_level}
- **置信度**: {self.style.confidence * 100:.0f}%

## Code Style
- 缩进: {self.style.indent}
- 命名: {self.style.naming}
- 范式: {self.style.paradigm}
- Type hints: {'是' if self.style.type_hints else '否'}

## Project
- 语言: {self.project.language}
- 框架: {', '.join(self.project.frameworks) if self.project.frameworks else '待发现'}
- 依赖: {len(self.project.dependencies)} 个

## Work Habits
- 活跃时段: {self.habits.peak_hours[:5]}
- 常用命令: {', '.join(c['name'] for c in self.habits.common_commands[:5]) if self.habits.common_commands else '待发现'}
- 风格: {'先分析再动手' if self.habits.prefers_plan_first else '直接上手'}"""

    def get_context_prompt(self) -> str:
        """生成注入 LLM 的上下文"""
        return f"""<growth_profile>
{self.identity_summary}

根据以上画像，调整你的回答风格以匹配用户的偏好。
</growth_profile>"""
