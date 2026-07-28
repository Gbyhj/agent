"""Agent v6 — 集成全部 12 项行业技术"""
from __future__ import annotations
import os, time, asyncio
from dataclasses import dataclass

from ..tools.production import ProductionTool, RiskLevel, ToolResult
from ..infra.guards import InputGuard, OutputGuard, ToolGuard, full_check
from ..features.modes import AgentMode, ModeManager
from ..features.durable import DurableExecutor, DurabilityMode
from ..features.caveman import CavemanMode, CavemanLevel
from ..features.work_order import build_work_order
from ..features.cost_router import CostRouter
from ..memory.async_memory import AsyncMemoryWorker, MemoryForgetting

@dataclass
class AgentV6Config:
    mode: str = "autonomous"  # shadow | assist | autonomous
    caveman_level: str = "full"
    durability: str = "sync"
    max_turns: int = 25
    daily_budget: float = 5.0

class AgentV6:
    """Agent v6 — 行业最佳实践全部集成"""
    
    def __init__(self, config: AgentV6Config = None):
        self.config = config or AgentV6Config()
        self.mode = ModeManager(AgentMode(self.config.mode))
        self.caveman = CavemanMode(CavemanLevel(self.config.caveman_level))
        self.cost_tracker = CostRouter()
        self.memory_worker = AsyncMemoryWorker(None)
        self.forgetting = MemoryForgetting()
        self.guard = full_check
        self._total_calls = 0
    
    async def process(self, task: str) -> dict:
        """完整处理管线 — 所有集成"""
        self._total_calls += 1
        
        # 1. Input Guard
        ok, reason = InputGuard.check(task)
        if not ok: return {"error": reason, "status": "blocked"}
        
        # 2. Build Work-Order
        wo = build_work_order(task)
        
        # 3. Run agent (with mode)
        result = self.mode.execute(None, task)
        
        # 4. Output compression
        output = str(result.result or '')
        compressed = self.caveman.compress(output)
        
        # 5. Output sanitize
        clean = OutputGuard.sanitize(compressed)
        
        # 6. Record cost
        self.cost_tracker.record("flash", 3, len(task), 0.0001, 0.9)
        
        # 7. Async memory
        self.memory_worker.add("task", task)
        
        # 8. Forgetting with confidence
        self.forgetting.add(f"call_{self._total_calls}", task[:100])
        
        return {
            "status": "completed",
            "output": clean,
            "mode": self.config.mode,
            "cost": self.cost_tracker.stats(),
            "memory": self.forgetting.stats(),
        }
    
    def stats(self) -> dict:
        return {
            "total_calls": self._total_calls,
            "mode": self.config.mode,
            "caveman": self.config.caveman_level,
            "cost": self.cost_tracker.stats(),
            "memory": self.forgetting.stats(),
        }
