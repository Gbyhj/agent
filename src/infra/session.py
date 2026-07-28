"""
Session State Machine — Grok Build 最强单点

Grok Build 的 session 生命周期是最优雅的状态机设计。

状态转换:
    idle → working → idle_resident → dormant → completed
      ↑       ↓            ↓
      └─ resume ← wake ────┘

用法:
    session = SessionManager()
    session.start()           # idle → working
    session.pause()           # working → idle_resident
    session.resume()          # idle_resident → working
    session.sleep()           # idle_resident → dormant
    session.wake()            # dormant → idle_resident
    session.complete()        # → completed
    session.fail("reason")    # → dead_failed
"""
from __future__ import annotations

from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json, os


class SessionState(Enum):
    IDLE = "idle"                       # 空闲，等待任务
    WORKING = "working"                 # 正在执行
    IDLE_RESIDENT = "idle_resident"     # 空闲但保持活跃（等待后续消息）
    DORMANT = "dormant"                 # 休眠（长时间无活动）
    COMPLETED = "completed"             # 正常完成
    DEAD_FAILED = "dead_failed"         # 异常终止


@dataclass
class Session:
    id: str
    state: SessionState = SessionState.IDLE
    task: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    turns: int = 0
    results: list[str] = field(default_factory=list)
    
    # 自动休眠阈值
    IDLE_RESIDENT_TIMEOUT = timedelta(minutes=30)
    DORMANT_TIMEOUT = timedelta(hours=4)
    DEAD_TIMEOUT = timedelta(days=7)
    
    @property
    def age(self) -> timedelta:
        return datetime.now() - datetime.fromisoformat(self.created_at)
    
    @property
    def idle_time(self) -> timedelta:
        return datetime.now() - datetime.fromisoformat(self.last_active)
    
    def touch(self):
        self.last_active = datetime.now().isoformat()
    
    def _auto_transition(self):
        """根据空闲时间自动转换状态"""
        if self.state == SessionState.IDLE_RESIDENT:
            if self.idle_time > self.DORMANT_TIMEOUT:
                self.state = SessionState.DORMANT
            # 休眠太久 → 清理
            if self.idle_time > self.DEAD_TIMEOUT:
                self.state = SessionState.DEAD_FAILED


class SessionManager:
    """
    会话管理器 — 学习 Grok Build 的生命周期设计
    
    持久化: ~/.agent_sessions/*.json
    """
    
    VALID_TRANSITIONS = {
        SessionState.IDLE:           [SessionState.WORKING],
        SessionState.WORKING:        [SessionState.IDLE_RESIDENT, SessionState.COMPLETED, SessionState.DEAD_FAILED],
        SessionState.IDLE_RESIDENT:  [SessionState.WORKING, SessionState.DORMANT],
        SessionState.DORMANT:        [SessionState.IDLE_RESIDENT, SessionState.DEAD_FAILED],
        SessionState.COMPLETED:      [],  # 终态
        SessionState.DEAD_FAILED:    [],  # 终态
    }
    
    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = storage_dir or os.path.expanduser("~/.agent_sessions")
        os.makedirs(self.storage_dir, exist_ok=True)
        self._sessions: dict[str, Session] = {}
        self._current_id: str | None = None
        self._load()
    
    def _load(self):
        for f in os.listdir(self.storage_dir):
            if f.endswith(".json"):
                try:
                    data = json.load(open(os.path.join(self.storage_dir, f)))
                    session = Session(
                        id=data["id"],
                        state=SessionState(data["state"]),
                        task=data.get("task", ""),
                        created_at=data.get("created_at", ""),
                        last_active=data.get("last_active", ""),
                        turns=data.get("turns", 0),
                        results=data.get("results", []),
                    )
                    session._auto_transition()
                    self._sessions[session.id] = session
                except Exception:
                    pass
    
    def _save(self, session: Session):
        data = {
            "id": session.id, "state": session.state.value,
            "task": session.task, "created_at": session.created_at,
            "last_active": session.last_active, "turns": session.turns,
            "results": session.results,
        }
        with open(os.path.join(self.storage_dir, f"{session.id}.json"), "w") as f:
            json.dump(data, f, indent=2)
    
    def create(self, task: str = "") -> Session:
        import uuid
        session = Session(id=uuid.uuid4().hex[:12], task=task)
        self._sessions[session.id] = session
        self._current_id = session.id
        self._save(session)
        return session
    
    def start(self, session_id: str | None = None) -> Session:
        session = self._sessions.get(session_id or self._current_id)
        if not session:
            session = self.create()
        session.state = SessionState.WORKING
        session.touch()
        self._current_id = session.id
        self._save(session)
        return session
    
    def pause(self):
        if session := self._current():
            session.state = SessionState.IDLE_RESIDENT
            session.touch()
            self._save(session)
    
    def resume(self) -> Session | None:
        if session := self._current():
            session.state = SessionState.WORKING
            session.touch()
            self._save(session)
        return session
    
    def complete(self, result: str = ""):
        if session := self._current():
            session.state = SessionState.COMPLETED
            if result: session.results.append(result)
            session.touch()
            self._save(session)
    
    def fail(self, reason: str):
        if session := self._current():
            session.state = SessionState.DEAD_FAILED
            session.results.append(f"FAILED: {reason}")
            session.touch()
            self._save(session)
    
    def _current(self) -> Session | None:
        return self._sessions.get(self._current_id) if self._current_id else None
    
    @property
    def current_state(self) -> str:
        session = self._current()
        return session.state.value if session else "no_session"
    
    def list_active(self) -> list[dict]:
        active = []
        for s in self._sessions.values():
            s._auto_transition()
            if s.state not in (SessionState.COMPLETED, SessionState.DEAD_FAILED):
                active.append({
                    "id": s.id, "state": s.state.value,
                    "task": s.task[:60], "idle": str(s.idle_time).split(".")[0],
                })
        return sorted(active, key=lambda x: x["idle"])
    
    def stats(self) -> dict:
        total = len(self._sessions)
        states = {}
        for s in self._sessions.values():
            s._auto_transition()
            states[s.state.value] = states.get(s.state.value, 0) + 1
        return {"total": total, "by_state": states, "current": self.current_state}

    # ── Agno: Fork 分支 (参考 Agno continue_run with fork=True) ──
    def fork(self, session_id: str | None = None, label: str = "") -> Session:
        """创建当前会话的分支 (不覆盖原会话)"""
        import uuid, copy
        original = self._sessions.get(session_id or self._current_id)
        if not original:
            return self.create(label or "fork")

        forked = copy.deepcopy(original)
        forked.id = uuid.uuid4().hex[:12]
        forked.state = SessionState.WORKING
        if label:
            forked.task = f"[Fork: {label}] {forked.task}"
        forked.created_at = datetime.now().isoformat()
        forked.last_active = forked.created_at
        forked.results = []  # 清空，新分支从零开始

        self._sessions[forked.id] = forked
        self._current_id = forked.id
        self._save(forked)
        return forked

    def list_branches(self) -> list[dict]:
        """列出所有分支 (包括历史会话)"""
        return [
            {"id": s.id, "task": s.task[:50], "state": s.state.value,
             "turns": s.turns, "created": s.created_at[:10]}
            for s in self._sessions.values()
        ]
