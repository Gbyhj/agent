"""
Project State — 会话驱动开发 (CDD)

灵感: OpenClaw HEARTBEAT × Grok Build Goal Tracker

Agent 维护一个持久化的项目状态板，跨会话保持上下文。

用法:
    pstate = ProjectState()
    pstate.add_task("实现用户认证", status="in_progress")
    ctx = pstate.get_context()  # 注入 LLM 上下文中
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta


class ProjectState:
    """
    持久化项目状态板

    文件: .project_state.md (人类可读写, git 可版本化)

    包含:
    - 当前任务 (TODO → IN_PROGRESS → DONE)
    - 最近决策 (为什么不选方案 A)
    - 已知问题 (bug 追踪)
    - 项目统计 (行数、文件数)
    """

    def __init__(self, path: str = "./.project_state.md"):
        self.path = path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.path):
            self._write("""# Project State

## Current
*(没有活跃任务)*

## Decisions
*(无记录)*

## Issues
*(无已知问题)*

## Stats
- Last updated: {now}

---
*Agent v5 自动维护*
""".replace("{now}", datetime.now().strftime("%Y-%m-%d %H:%M")))

    def _read(self) -> str:
        with open(self.path, encoding="utf-8") as f:
            return f.read()

    def _write(self, content: str):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(content)

    # ── 任务管理 ──────────────────────────────
    def add_task(self, title: str, status: str = "todo", details: str = ""):
        """添加或更新任务"""
        content = self._read()
        now = datetime.now().strftime("%Y-%m-%d")
        task_line = f"- [{ 'x' if status == 'done' else ' '}] {title}"
        if details:
            task_line += f" — {details}"
        task_line += f" ({now})"

        # 合并到 Current section
        if "## Current" in content:
            section_start = content.index("## Current")
            next_section = content.find("\n## ", section_start + 1)
            if next_section == -1: next_section = len(content)

            # 检查是否已存在同标题任务
            existing = re.search(rf'- \[[ x]\] {re.escape(title)}', content[section_start:next_section])
            if existing:
                # 更新状态
                content = content.replace(existing.group(), task_line)
            else:
                # 追加
                content = content[:next_section] + task_line + "\n" + content[next_section:]

        self._write(content)

    def complete_task(self, title: str, summary: str = ""):
        """标记任务完成"""
        self.add_task(title, status="done", details=summary)

    def get_active_tasks(self) -> list[str]:
        """获取活跃任务列表"""
        content = self._read()
        tasks = re.findall(r'- \[ \] (.+)', content)
        return tasks

    # ── 决策记录 ──────────────────────────────
    def record_decision(self, topic: str, choice: str, reason: str):
        """记录重要决策"""
        content = self._read()
        now = datetime.now().strftime("%Y-%m-%d")
        entry = f"- **{topic}**: {choice} — *{reason}* ({now})\n"

        if "## Decisions" in content:
            section_start = content.index("## Decisions")
            next_section = content.find("\n## ", section_start + 1)
            if next_section == -1: next_section = len(content)
            content = content[:next_section] + entry + content[next_section:]

        self._write(content)

    # ── 问题追踪 ──────────────────────────────
    def log_issue(self, title: str, severity: str = "minor", details: str = ""):
        """记录已知问题"""
        content = self._read()
        now = datetime.now().strftime("%Y-%m-%d")
        sev_map = {"critical": "🔴", "major": "🟡", "minor": "🟢"}
        icon = sev_map.get(severity, "⚪")
        entry = f"- {icon} {title}"
        if details: entry += f" — {details}"
        entry += f" ({now})\n"

        if "## Issues" in content:
            section_start = content.index("## Issues")
            next_section = content.find("\n## ", section_start + 1)
            if next_section == -1: next_section = len(content)
            content = content[:next_section] + entry + content[next_section:]

        self._write(content)

    def resolve_issue(self, title: str):
        """标记问题已解决"""
        content = self._read()
        content = re.sub(rf'- [🔴🟡🟢⚪] {re.escape(title)}.*\n', '', content)
        self._write(content)

    # ── 上下文注入 ────────────────────────────
    def get_context(self, max_chars: int = 2000) -> str:
        """生成注入 LLM 的上下文"""
        content = self._read()

        # 更新最后更新时间和统计
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = re.sub(r'- Last updated: .*', f'- Last updated: {now}', content)

        # 统计项目文件（如果存在）
        if os.path.exists("agent"):
            py_files = sum(1 for _ in os.walk("agent") if any(f.endswith(".py") for f in _[2] if not f.startswith(".")))
            if py_files:
                content = re.sub(r'- (Python files): .*', rf'- \1: {py_files}', content)
                if "Python files" not in content:
                    content = content.replace("## Stats\n", f"## Stats\n- Python files: {py_files}\n")

        self._write(content)

        # 构建上下文块
        tasks = self.get_active_tasks()
        task_block = ""
        if tasks:
            task_block = "\n".join(f"- {t[:80]}" for t in tasks[:5])

        ctx = "<project_state>"
        if task_block:
            ctx += f"\n**活跃任务**:\n{task_block}"

        # 提取最近的决策
        decisions = re.findall(r'- \*\*(.+?)\*\*: (.+?) — (.+?) \(', content)
        if decisions:
            ctx += "\n**最近决策**:"
            for topic, choice, reason in decisions[-3:]:
                ctx += f"\n- {topic}: {choice} ({reason})"

        # 提取已知问题
        issues = re.findall(r'- ([🔴🟡🟢⚪]) (.+)', content)
        if issues:
            ctx += "\n**已知问题**:"
            for icon, desc in issues[-3:]:
                ctx += f"\n- {icon} {desc[:80]}"

        ctx += "\n</project_state>"
        return ctx[:max_chars]
