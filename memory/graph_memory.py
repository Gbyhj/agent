"""
Graph Memory — Mem0 实体图谱检索

参考 Mem0 源码:
- entity_store: data + entity_type + linked_memory_ids
- 实体惩罚: 1/(1 + 0.001 × (n-1)²)
- 相似度≥0.95视为同一实体
- 三路融合: semantic + BM25 + entity_boost
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any


class GraphMemory:
    """实体关系图谱记忆"""

    ENTITY_BOOST_WEIGHT = 0.5
    SIMILARITY_THRESHOLD = 0.5  # 匹配阈值
    MERGE_THRESHOLD = 0.95       # 合并阈值

    def __init__(self, path: str | None = None):
        self.path = path or os.path.expanduser("~/.agent_graph_memory.json")
        self._entities: dict[str, dict] = {}  # entity_id → {data, type, linked_memory_ids}
        self._memory_entities: dict[str, list[str]] = {}  # memory_id → [entity_ids]
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                data = json.load(open(self.path, encoding="utf-8"))
                self._entities = data.get("entities", {})
                self._memory_entities = data.get("links", {})
            except Exception:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {"entities": self._entities, "links": self._memory_entities},
                f, ensure_ascii=False, indent=2,
            )

    # ── 实体提取 ──
    def extract(self, text: str) -> list[dict]:
        """从文本提取结构化实体"""
        import re
        entities = []

        # 简单命名实体提取
        patterns = {
            "技术": [r"\b(Python|Java|Go|Rust|TypeScript|React|Docker|Kubernetes|API|SQL)\b"],
            "框架": [r"\b(Flask|Django|FastAPI|Spring|Next\.?js|Vue)\b"],
            "概念": [r"\b(Agent|LLM|RAG|MCP|A2A|微服务|单点登录)\b"],
        }

        for etype, pats in patterns.items():
            for pat in pats:
                for match in re.findall(pat, text, re.IGNORECASE):
                    entities.append({"type": etype, "data": match})

        return entities

    # ── 实体链接 ──
    def link(self, memory_id: str, entities: list[dict]):
        """建立记忆→实体链接"""
        for entity in entities:
            key = f"{entity['type']}:{entity['data'].lower()}"
            entity_id = hashlib.md5(key.encode()).hexdigest()[:12]

            if entity_id in self._entities:
                # 已有实体: 追加链接
                if memory_id not in self._entities[entity_id]["linked_memory_ids"]:
                    self._entities[entity_id]["linked_memory_ids"].append(memory_id)
            else:
                # 新实体
                self._entities[entity_id] = {
                    "type": entity["type"],
                    "data": entity["data"],
                    "linked_memory_ids": [memory_id],
                }

            # 反向链接
            self._memory_entities.setdefault(memory_id, [])
            if entity_id not in self._memory_entities[memory_id]:
                self._memory_entities[memory_id].append(entity_id)

        self._save()

    # ── 图谱加权检索 ──
    def boost_search(self, query: str, semantic_results: list[tuple[str, float]]) -> dict[str, float]:
        """
        实体加权检索

        Mem0 核心公式:
        boost = similarity × ENTITY_BOOST_WEIGHT × memory_count_penalty
        memory_count_penalty = 1/(1 + 0.001 × (n-1)²)
        """
        query_entities = self.extract(query)
        if not query_entities:
            return {}

        boosts: dict[str, float] = {}

        for entity in query_entities:
            key = f"{entity['type']}:{entity['data'].lower()}"
            entity_id = hashlib.md5(key.encode()).hexdigest()[:12]

            if entity_id not in self._entities:
                continue

            ent = self._entities[entity_id]
            linked = ent["linked_memory_ids"]
            num_linked = max(len(linked), 1)

            # Mem0 惩罚因子公式
            memory_count_penalty = 1.0 / (1.0 + 0.001 * ((num_linked - 1) ** 2))
            boost = 1.0 * self.ENTITY_BOOST_WEIGHT * memory_count_penalty  # 精确匹配视为1.0

            for memory_id in linked:
                boosts[memory_id] = max(boosts.get(memory_id, 0), boost)

        return boosts

    def hybrid_search(self, query: str, semantic_results: list[tuple[str, float]]) -> list[tuple[str, float]]:
        """
        混合检索: 语义分数 + 实体加权

        参考 Mem0 score_and_rank: 乘法融合
        """
        boosts = self.boost_search(query, semantic_results)

        scored = []
        for mem_id, semantic_score in semantic_results:
            entity_boost = boosts.get(mem_id, 1.0)
            final_score = semantic_score * entity_boost  # 乘法融合
            scored.append((mem_id, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def stats(self) -> dict:
        return {
            "total_entities": len(self._entities),
            "total_links": sum(len(v) for v in self._memory_entities.values()),
            "avg_linked": sum(len(e["linked_memory_ids"]) for e in self._entities.values()) / max(len(self._entities), 1),
        }
