"""
Agent Time Travel — Agent 时间旅行

灵感: LangGraph Checkpointer × Git branch

每一步自动 checkpoint，可回退到任意历史节点，创建分支探索不同方案。
像 git bisect 一样调试 Agent 决策。

用法:
    traveler = TimeTraveler()
    traveler.checkpoint(state)        # 保存快照
    traveler.rollback(step=3)         # 回退到第 3 步
    traveler.branch("try-another")    # 创建分支
    traveler.compare(branch_a, branch_b)  # 对比两个分支
"""
from __future__ import annotations

import os
import json
import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Checkpoint:
    """单个快照"""
    step: int
    state: dict            # AgentState 的深拷贝
    timestamp: str
    label: str = ""
    parent_branch: str = "main"


@dataclass
class Branch:
    """执行分支"""
    name: str
    checkpoints: list[Checkpoint] = field(default_factory=list)
    final_answer: str = ""
    total_turns: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class TimeTraveler:
    """
    Agent 时间旅行器

    像 git 一样管理 Agent 执行历史：
    - checkpoint: 保存快照（类似 git commit）
    - rollback: 回退到历史点（类似 git reset）
    - branch: 创建探索分支（类似 git branch）
    - compare: 对比分支结果

    存储: ~/.agent_timeline/
    """

    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = storage_dir or os.path.expanduser("~/.agent_timeline")
        self._branches: dict[str, Branch] = {"main": Branch("main")}
        self._current_branch = "main"
        self._load()

    def _load(self):
        os.makedirs(self.storage_dir, exist_ok=True)
        meta_path = os.path.join(self.storage_dir, "meta.json")
        if os.path.exists(meta_path):
            try:
                data = json.load(open(meta_path, encoding="utf-8"))
                self._current_branch = data.get("current", "main")
                for name, bdata in data.get("branches", {}).items():
                    branch = Branch(name)
                    branch.final_answer = bdata.get("final_answer", "")
                    branch.total_turns = bdata.get("total_turns", 0)
                    branch.created_at = bdata.get("created_at", "")
                    self._branches[name] = branch
            except Exception:
                pass

    def _save_meta(self):
        data = {
            "current": self._current_branch,
            "branches": {
                name: {
                    "final_answer": b.final_answer,
                    "total_turns": b.total_turns,
                    "created_at": b.created_at,
                }
                for name, b in self._branches.items()
            }
        }
        with open(os.path.join(self.storage_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def checkpoint(self, state: dict, step: int, label: str = ""):
        """保存快照"""
        branch = self._branches[self._current_branch]
        cp = Checkpoint(
            step=step,
            state=copy.deepcopy(state),
            timestamp=datetime.now().isoformat(),
            label=label or f"Step {step}",
            parent_branch=self._current_branch,
        )
        branch.checkpoints.append(cp)

        # 持久化大型 state 到文件
        cp_path = os.path.join(self.storage_dir, f"{self._current_branch}_{step}.json")
        with open(cp_path, "w", encoding="utf-8") as f:
            json.dump(cp.__dict__, f, default=str, indent=2)

        self._save_meta()

    def rollback(self, step: int) -> dict | None:
        """回退到指定步骤"""
        branch = self._branches[self._current_branch]
        for cp in reversed(branch.checkpoints):
            if cp.step <= step:
                # 截断后续的 checkpoint
                branch.checkpoints = branch.checkpoints[:branch.checkpoints.index(cp) + 1]
                self._save_meta()
                return cp.state
        return None

    def branch(self, name: str) -> str:
        """创建新分支"""
        if name in self._branches:
            name = f"{name}_{len(self._branches)}"
        self._branches[name] = Branch(name)
        self._current_branch = name
        self._save_meta()
        return name

    def switch(self, branch_name: str):
        """切换分支"""
        if branch_name in self._branches:
            self._current_branch = branch_name
            self._save_meta()

    def finish(self, answer: str, turns: int):
        """标记分支完成"""
        branch = self._branches[self._current_branch]
        branch.final_answer = answer
        branch.total_turns = turns
        self._save_meta()

    def compare(self, branch_a: str, branch_b: str) -> dict:
        """对比两个分支"""
        a = self._branches.get(branch_a)
        b = self._branches.get(branch_b)
        if not a or not b:
            return {"error": "Branch not found"}

        return {
            f"{branch_a}": {
                "turns": a.total_turns,
                "answer_preview": (a.final_answer or "")[:100],
                "checkpoints": len(a.checkpoints),
            },
            f"{branch_b}": {
                "turns": b.total_turns,
                "answer_preview": (b.final_answer or "")[:100],
                "checkpoints": len(b.checkpoints),
            },
            "winner": branch_a if a.total_turns < b.total_turns else branch_b,
            "reason": f"更少轮次 ({min(a.total_turns, b.total_turns)} vs {max(a.total_turns, b.total_turns)})",
        }

    def timeline(self) -> list[dict]:
        """获取时间线概览"""
        return [
            {
                "branch": name,
                "checkpoints": len(b.checkpoints),
                "turns": b.total_turns,
                "answer": (b.final_answer or "")[:60],
                "created": b.created_at[:10],
            }
            for name, b in self._branches.items()
        ]

    def stats(self) -> dict:
        branches = len(self._branches)
        total_checkpoints = sum(len(b.checkpoints) for b in self._branches.values())
        completed = sum(1 for b in self._branches.values() if b.final_answer)
        return {
            "branches": branches,
            "total_checkpoints": total_checkpoints,
            "completed_branches": completed,
            "current_branch": self._current_branch,
        }
