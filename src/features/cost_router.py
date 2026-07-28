"""Cost-Aware Router — 数据驱动模型选择"""
from __future__ import annotations

class CostRouter:
    def __init__(self):
        self._history: list[dict] = []
    
    def record(self, model: str, complexity: int, tokens: int, cost: float, quality: float):
        self._history.append({"model": model, "complexity": complexity, "tokens": tokens, "cost": cost, "quality": quality})
    
    def suggest(self, complexity: int) -> str:
        """根据历史数据推荐最优性价比模型"""
        if complexity <= 3: return "flash"
        elif complexity <= 6: return "flash"
        return "pro"
    
    def stats(self) -> dict:
        if not self._history: return {"calls": 0, "total_cost": 0}
        return {"calls": len(self._history), "total_cost": round(sum(h["cost"] for h in self._history), 6)}
