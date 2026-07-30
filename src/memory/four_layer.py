"""四层记忆架构 — 对标 LinkedIn QCon 2026

Layer 1: 对话记忆 (Conversational) — 当前会话, 短期
Layer 2: 情景记忆 (Episodic)      — 过去交互, 发生了什么
Layer 3: 语义记忆 (Semantic)      — 推断事实, 知道什么
Layer 4: 程序性记忆 (Procedural)  — 工作流, 怎么做的

核心创新 (vs 现有): 
  - 可写记忆 (Agent 能编辑重构, 而非仅追加)
  - 置信度衰减 (随时间遗忘)
  - 冲突解决 (新旧事实合并)
"""
import time, json, os
from dataclasses import dataclass, field
from collections import OrderedDict

@dataclass
class MemoryFact:
    content: str
    source: str = ""
    confidence: float = 1.0
    created: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0
    
    def __post_init__(self):
        if not self.created: self.created = time.time()
        if not self.last_accessed: self.last_accessed = time.time()

class FourLayerMemory:
    """四层记忆 — Agent 持续学习的基础"""
    
    def __init__(self, path: str = None):
        self.path = path or os.path.join(os.path.dirname(__file__), "..", "..", ".agent_memory", "four_layer.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        
        # L1: 对话 (LRU 50项)
        self.conversational: OrderedDict[str, str] = OrderedDict()
        # L2: 情景 (最近100次交互)
        self.episodic: list[MemoryFact] = []
        # L3: 语义 (推断知识, 可编辑)
        self.semantic: dict[str, MemoryFact] = {}
        # L4: 程序性 (工作流模板)
        self.procedural: dict[str, list[str]] = {}
        
        self._load()
    
    # —— L1: 对话记忆 ——
    def add_conversation(self, turn_id: str, content: str):
        self.conversational[turn_id] = content
        if len(self.conversational) > 50:
            self.conversational.popitem(last=False)
    
    def get_recent_conversation(self, n: int = 10) -> str:
        items = list(self.conversational.items())[-n:]
        return "\n".join(f"[{k[:8]}] {v[:200]}" for k, v in items)
    
    # —— L2: 情景记忆 ——
    def add_episode(self, content: str, source: str = ""):
        fact = MemoryFact(content=content, source=source)
        self.episodic.append(fact)
        if len(self.episodic) > 100:
            self.episodic = self.episodic[-100:]
        self._save()
    
    def recall_episodes(self, keyword: str, n: int = 5) -> list:
        matches = [e for e in self.episodic if keyword.lower() in e.content.lower()]
        return sorted(matches, key=lambda e: -e.created)[:n]
    
    # —— L3: 语义记忆 (可编辑 — 对标 "能编辑的Agent学得快") ——
    def learn_fact(self, key: str, value: str, confidence: float = 1.0):
        if key in self.semantic:
            # 冲突解决: 新事实合并
            existing = self.semantic[key]
            if confidence > existing.confidence:
                existing.content = value
                existing.confidence = confidence
            existing.last_accessed = time.time()
            existing.access_count += 1
        else:
            self.semantic[key] = MemoryFact(content=value, confidence=confidence)
        self._save()
    
    def recall_fact(self, key: str) -> str | None:
        if key in self.semantic:
            f = self.semantic[key]
            f.last_accessed = time.time()
            f.access_count += 1
            return f.content
        return None
    
    def edit_fact(self, key: str, new_value: str):
        """Agent 编辑语义记忆 (结构重组, 非仅追加)"""
        if key in self.semantic:
            self.semantic[key].content = new_value
        else:
            self.semantic[key] = MemoryFact(content=new_value)
        self._save()
    
    def forget_stale(self, ttl_days: int = 30):
        """遗忘过时事实 — 对标 Mem0 遗忘机制"""
        now = time.time()
        threshold = now - ttl_days * 86400
        before = len(self.semantic)
        self.semantic = {
            k: v for k, v in self.semantic.items()
            if v.last_accessed > threshold or v.confidence > 0.8
        }
        after = len(self.semantic)
        return before - after  # forgotten count
    
    # —— L4: 程序性记忆 ——
    def learn_procedure(self, task_type: str, steps: list[str]):
        """记录'怎么做' — 下次同类任务直接复用"""
        if task_type in self.procedural:
            # 合并优化
            self.procedural[task_type] = list(dict.fromkeys(
                self.procedural[task_type][-3:] + steps
            ))
        else:
            self.procedural[task_type] = steps
        self._save()
    
    def recall_procedure(self, task_type: str) -> list[str]:
        return self.procedural.get(task_type, [])
    
    # —— 综合检索 ——
    def get_context_for_llm(self, max_chars: int = 2000) -> str:
        """生成注入 LLM 的上下文摘要"""
        parts = []
        
        # 语义记忆: 已知的关键事实
        if self.semantic:
            top = sorted(self.semantic.values(), 
                        key=lambda f: (f.confidence * f.access_count), reverse=True)[:5]
            parts.append("【已知事实】\n" + "\n".join(
                f"- {f.content}" for f in top
            ))
        
        # 程序性: 当前任务的已知工作流
        recent_procedures = list(self.procedural.items())[-2:]
        if recent_procedures:
            for task, steps in recent_procedures:
                parts.append(f"【工作流: {task}】\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps[:5])))
        
        # 情景: 最近交互
        if self.episodic:
            recent = self.episodic[-3:]
            parts.append("【最近事件】\n" + "\n".join(f"- {e.content[:120]}" for e in recent))
        
        return "\n\n".join(parts)[:max_chars]
    
    def stats(self) -> dict:
        return {
            "conversational": len(self.conversational),
            "episodic": len(self.episodic),
            "semantic": len(self.semantic),
            "procedural": len(self.procedural),
            "total_facts": len(self.semantic) + len(self.episodic),
        }
    
    def _save(self):
        data = {
            "episodic": [{"c": f.content, "s": f.source, "conf": f.confidence, "t": f.created} 
                        for f in self.episodic[-50:]],
            "semantic": {k: {"c": v.content, "conf": v.confidence, "t": v.created}
                        for k, v in self.semantic.items()},
            "procedural": self.procedural,
        }
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    
    def _load(self):
        if os.path.exists(self.path):
            try:
                data = json.load(open(self.path, encoding='utf-8'))
                for e in data.get("episodic", []):
                    self.episodic.append(MemoryFact(content=e["c"], source=e.get("s",""), 
                                                     confidence=e.get("conf",1.0), created=e.get("t",0)))
                for k, v in data.get("semantic", {}).items():
                    self.semantic[k] = MemoryFact(content=v["c"], confidence=v.get("conf",1.0), 
                                                   created=v.get("t",0))
                self.procedural = data.get("procedural", {})
            except Exception:
                pass
