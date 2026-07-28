"""
Heartbeat Scheduler — OpenClaw 最强单点

Agent 不等待用户指令，而是主动检查并执行任务。

参考 OpenClaw HEARTBEAT.md:
- 每 N 分钟检查一次
- 发现未完成任务 → 自动执行
- 发现有新消息 → 处理
- 发现有定时任务 → 执行

用法:
    heartbeat = Heartbeat(agent, interval_minutes=5)
    heartbeat.start()
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    name: str
    prompt: str              # Agent 任务描述
    cron: str = ""           # cron 表达式（简化为间隔分钟）
    interval_minutes: int = 60
    last_run: str = ""
    next_run: str = ""
    enabled: bool = True
    
    @property
    def is_due(self) -> bool:
        if not self.enabled: return False
        if not self.last_run: return True
        last = datetime.fromisoformat(self.last_run)
        return datetime.now() > last + timedelta(minutes=self.interval_minutes)


class Heartbeat:
    """
    心跳调度器

    三层检查（按优先级）:
    1. 待处理消息（如果有消息平台接入）
    2. 未完成项目任务（project_state.md 中的 todo）
    3. 定时任务（cron 调度）
    """

    def __init__(self, agent=None, interval_minutes: int = 5):
        self.agent = agent
        self.interval = interval_minutes
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._last_check: str = ""
        self._check_count: int = 0
        self._actions_taken: int = 0

    def add_task(self, name: str, prompt: str, interval_minutes: int = 60):
        """添加定时任务"""
        import uuid
        task = ScheduledTask(
            id=uuid.uuid4().hex[:8],
            name=name,
            prompt=prompt,
            interval_minutes=interval_minutes,
        )
        self._tasks[task.id] = task
        return task.id

    def remove_task(self, task_id: str):
        self._tasks.pop(task_id, None)

    async def start(self):
        """启动心跳循环"""
        self._running = True
        while self._running:
            await self._tick()
            await asyncio.sleep(self.interval * 60)

    def stop(self):
        self._running = False

    async def _tick(self):
        """一次心跳检查"""
        self._check_count += 1
        self._last_check = datetime.now().isoformat()
        actions = []

        # 1. 检查未完成项目任务
        try:
            from .project_state import ProjectState
            ps = ProjectState()
            active_tasks = ps.get_active_tasks()
            if active_tasks and self.agent:
                task = active_tasks[0]  # 取最优先的
                result = await self.agent.run(f"继续执行未完成任务: {task}")
                actions.append(f"执行项目任务: {task[:50]}")
                if "完成" in (result.final_answer or ""):
                    ps.complete_task(task, result.final_answer[:100])
        except Exception:
            pass

        # 2. 检查定时任务
        for task in self._tasks.values():
            if task.is_due and self.agent:
                try:
                    await self.agent.run(task.prompt)
                    task.last_run = datetime.now().isoformat()
                    task.next_run = (datetime.now() + timedelta(minutes=task.interval_minutes)).isoformat()
                    actions.append(f"定时任务: {task.name}")
                except Exception:
                    pass

        self._actions_taken += len(actions)

    def stats(self) -> dict:
        return {
            "checks": self._check_count,
            "actions_taken": self._actions_taken,
            "last_check": self._last_check[:19] if self._last_check else "never",
            "scheduled_tasks": len(self._tasks),
            "active_tasks": sum(1 for t in self._tasks.values() if t.enabled),
        }

    def list_tasks(self) -> list[dict]:
        return [
            {"name": t.name, "prompt": t.prompt[:60], "interval": f"{t.interval_minutes}min",
             "last_run": t.last_run[:19] if t.last_run else "never", "enabled": t.enabled}
            for t in self._tasks.values()
        ]
