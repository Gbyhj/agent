"""
Vector Memory — ChromaDB 语义记忆层

设计融合:
- ChromaDB: 轻量级 AI 原生向量数据库 (pip install 即用)
- Mem0: 向量+图谱混合记忆 (21+ 框架集成)
- OpenClaw: 记忆注入 LLM 上下文

架构:
    对话/经验 → 自动提取记忆 → Embedding 向量化 → ChromaDB 存储
    → 查询时语义检索 → 注入 LLM 上下文

使用:
    mem = VectorMemory()
    mem.remember("用户偏好使用 DeepSeek 模型", category="preference")
    results = mem.recall("用户用什么模型")
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    category: str = "general"
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class VectorMemory:
    """
    语义记忆层

    两层存储:
    1. ChromaDB: 向量嵌入 + 语义搜索 (如果 chromadb 可用)
    2. JSON fallback: 简单 key-value 存储 (无依赖)
    """

    def __init__(self, persist_dir: str = "./.agent_memory/vector"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        self._chroma = None
        self._collection = None
        self._fallback_file = os.path.join(persist_dir, "memories.json")
        self._fallback: list[dict] = self._load_fallback()

        # 尝试初始化 ChromaDB
        try:
            import chromadb
            self._chroma = chromadb.PersistentClient(path=os.path.join(persist_dir, "chroma"))
            self._collection = self._chroma.get_or_create_collection(
                name="agent_memories",
                metadata={"hnsw:space": "cosine"}
            )
        except (ImportError, Exception):
            pass

    def remember(self, content: str, category: str = "general", metadata: dict | None = None) -> str:
        """
        存储记忆

        Args:
            content: 记忆内容
            category: 分类 (preference, fact, skill, convention, ...)
            metadata: 附加元数据
        Returns:
            记忆 ID
        """
        import uuid
        mem_id = f"mem_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        meta = metadata or {}
        meta.update({"category": category, "created_at": now})

        if self._collection:
            try:
                self._collection.add(
                    ids=[mem_id],
                    documents=[content],
                    metadatas=[meta],
                )
                return mem_id
            except Exception:
                pass

        # Fallback
        self._fallback.append({"id": mem_id, "content": content, "metadata": meta})
        self._save_fallback()
        return mem_id

    def recall(self, query: str, category: str | None = None, top_k: int = 5) -> list[MemoryEntry]:
        """
        语义检索记忆

        Args:
            query: 查询文本
            category: 限定分类
            top_k: 返回条数
        """
        results = []

        if self._collection:
            try:
                where = {"category": category} if category else None
                chroma_results = self._collection.query(
                    query_texts=[query], n_results=top_k, where=where,
                )
                for i, doc_id in enumerate(chroma_results.get("ids", [[]])[0]):
                    results.append(MemoryEntry(
                        id=doc_id,
                        content=chroma_results["documents"][0][i],
                        category=chroma_results.get("metadatas", [[{}]])[0][i].get("category", "general"),
                        metadata=chroma_results.get("metadatas", [[{}]])[0][i],
                    ))
                return results
            except Exception:
                pass

        # Fallback: 简单关键词匹配
        query_lower = query.lower()
        scored = []
        for m in self._fallback:
            if category and m.get("metadata", {}).get("category") != category:
                continue
            # 简单评分：内容中包含查询词越多分越高
            score = sum(1 for w in query_lower.split() if w in m["content"].lower())
            if score > 0:
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        for _, m in scored[:top_k]:
            results.append(MemoryEntry(
                id=m["id"], content=m["content"],
                category=m.get("metadata", {}).get("category", "general"),
                metadata=m.get("metadata", {}),
            ))

        return results

    def forget(self, memory_id: str) -> bool:
        """删除记忆"""
        if self._collection:
            try:
                self._collection.delete(ids=[memory_id])
            except Exception:
                pass
        self._fallback = [m for m in self._fallback if m["id"] != memory_id]
        self._save_fallback()
        return True

    def list_all(self, category: str | None = None) -> list[MemoryEntry]:
        """列出所有记忆"""
        results = []
        if self._collection:
            try:
                where = {"category": category} if category else None
                data = self._collection.get(where=where)
                for i, doc_id in enumerate(data.get("ids", [])):
                    results.append(MemoryEntry(
                        id=doc_id, content=data["documents"][i],
                        category=data.get("metadatas", [{}])[i].get("category", "general"),
                    ))
            except Exception:
                pass

        if not results:
            for m in self._fallback:
                if category and m.get("metadata", {}).get("category") != category:
                    continue
                results.append(MemoryEntry(
                    id=m["id"], content=m["content"],
                    category=m.get("metadata", {}).get("category", "general"),
                ))
        return results

    def inject_context(self, query: str, max_chars: int = 2000) -> str:
        """检索相关记忆并构建上下文注入 LLM"""
        memories = self.recall(query, top_k=5)
        if not memories:
            return ""

        lines = ["<relevant_memories>"]
        for m in memories:
            lines.append(f"- [{m.category}] {m.content[:200]}")
        lines.append("</relevant_memories>")

        ctx = "\n".join(lines)
        return ctx[:max_chars]

    def stats(self) -> dict:
        """记忆统计"""
        count = 0
        if self._collection:
            try:
                count = self._collection.count()
            except Exception:
                count = len(self._fallback)
        return {
            "total_entries": count,
            "storage": "chromadb" if self._collection else "json_fallback",
            "persist_dir": self.persist_dir,
        }

    # ── fallback ──────────────────────────────
    def _load_fallback(self) -> list[dict]:
        if os.path.exists(self._fallback_file):
            try:
                with open(self._fallback_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_fallback(self):
        with open(self._fallback_file, "w", encoding="utf-8") as f:
            json.dump(self._fallback, f, ensure_ascii=False, indent=2)
