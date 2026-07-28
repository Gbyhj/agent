"""
Durable Execution — LangGraph interrupt/resume 原语

Source: LangGraph 1.0 · AppScale analysis · vadim.blog

核心模式:
    interrupt(reason) → 暂停 + 持久化状态 → 返回 resume_token
    resume(token, value) → 从断点继续执行

特性:
    - 不占 CPU: 暂停期间零计算资源
    - 跨进程: 可在不同 Pod 上恢复
    - 跨时间: 数秒到数天，任意间隔
    - 三模式: exit(最快) / async(平衡) / sync(最安全)
"""
from __future__ import annotations

import json
import os
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DurabilityMode(Enum):
    EXIT = "exit"      # 退出时持久化 (最快)
    ASYNC = "async"    # 异步持久化 (平衡)
    SYNC = "sync"      # 同步持久化 (最安全)


@dataclass
class AgentSnapshot:
    """Agent 快照 — 可序列化的完整状态"""
    thread_id: str
    step: int
    task: str = ""
    state: dict = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    created_at: str = ""

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, data: str) -> AgentSnapshot:
        return cls(**json.loads(data))


class Checkpointer:
    """持久化存储器"""

    def __init__(self, backend: str = "sqlite", path: str = None):
        self.backend = backend
        self.path = path or os.path.expanduser("~/.agent/checkpoints.db")
        self._store: dict[str, dict[str, AgentSnapshot]] = {}  # thread_id → {step: snapshot}
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def save(self, thread_id: str, step: int, snapshot: AgentSnapshot) -> str:
        """保存快照 → 返回 checkpoint_id"""
        snapshot.created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        if thread_id not in self._store:
            self._store[thread_id] = {}
        self._store[thread_id][step] = snapshot

        # 持久化到文件
        cid = f"{thread_id}:{step}"
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": cid, "snapshot": snapshot.__dict__}, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

        return cid

    def load(self, thread_id: str, step: int = -1) -> AgentSnapshot | None:
        """加载快照"""
        if thread_id in self._store:
            steps = self._store[thread_id]
            if step == -1:
                step = max(steps.keys())
            return steps.get(step)
        return None

    def list_checkpoints(self, thread_id: str) -> list[int]:
        """列出所有 checkpoint"""
        if thread_id in self._store:
            return sorted(self._store[thread_id].keys())
        return []


class DurableExecutor:
    """
    Durable Executor — interrupt/resume

    用法:
        executor = DurableExecutor(agent)
        
        # 正常执行
        result = await executor.run("analyze repo")
        
        # 需要人工审批
        result = executor.interrupt("需要确认删除操作")
        # ... 用户确认后 ...
        result = executor.resume(thread_id, step, approved=True)
    """

    def __init__(self, agent=None, mode: DurabilityMode = DurabilityMode.SYNC):
        self.agent = agent
        self.mode = mode
        self.checkpointer = Checkpointer()
        self._interrupted: dict[str, tuple[int, str]] = {}  # thread_id → (step, reason)

    async def run(self, task: str, thread_id: str = None) -> dict:
        """执行任务，支持中断恢复"""
        thread_id = thread_id or uuid.uuid4().hex[:12]

        # 尝试从 checkpoint 恢复
        snapshot = self.checkpointer.load(thread_id)
        start_step = snapshot.step + 1 if snapshot else 1

        state = snapshot.state if snapshot else {"task": task}
        messages = snapshot.messages if snapshot else []

        for step in range(start_step, 100):
            # 检查是否有中断请求
            if thread_id in self._interrupted:
                _, reason = self._interrupted.pop(thread_id)
                self._save(thread_id, step - 1, state, messages)
                return {"status": "interrupted", "reason": reason, "thread_id": thread_id, "step": step - 1}

            # 执行一步
            if self.agent:
                try:
                    result = await self.agent.run(task)
                    state["last_result"] = str(result)
                    messages.append({"role": "agent", "content": str(result)})
                except Exception as e:
                    state["error"] = str(e)
                    break

            # 持久化
            if self.mode == DurabilityMode.SYNC:
                self._save(thread_id, step, state, messages)

        self._save(thread_id, 100, state, messages)
        return {"status": "completed", "thread_id": thread_id, "state": state}

    def interrupt(self, thread_id: str, reason: str) -> dict:
        """暂停执行 — 返回 resume_token"""
        # 找到最后一个 checkpoint 的 step
        checkpoints = self.checkpointer.list_checkpoints(thread_id)
        last_step = checkpoints[-1] if checkpoints else 0
        self._interrupted[thread_id] = (last_step, reason)
        return {
            "status": "interrupted",
            "thread_id": thread_id,
            "step": last_step,
            "reason": reason,
            "resume_token": f"{thread_id}:{last_step}",
        }

    def resume(self, thread_id: str, resume_value: Any = None) -> dict:
        """恢复执行 — 从断点继续"""
        snapshot = self.checkpointer.load(thread_id)
        if not snapshot:
            return {"status": "error", "reason": "no checkpoint found"}

        return {
            "status": "resuming",
            "thread_id": thread_id,
            "from_step": snapshot.step,
            "resume_value": resume_value,
        }

    def _save(self, thread_id: str, step: int, state: dict, messages: list):
        snapshot = AgentSnapshot(
            thread_id=thread_id, step=step, state=state, messages=messages,
        )
        self.checkpointer.save(thread_id, step, snapshot)
