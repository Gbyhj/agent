"""
Async Memory Pipeline — CallSphere 模式

Memory extraction runs on background thread, never blocks main request.

Source: CallSphere · Letta · Mem0 production patterns
Pattern: User→Agent→Response(inline) └→Queue→Worker→Extract→Update→Upsert
"""
from __future__ import annotations

import threading
import queue
import time
import os
from typing import Any


class AsyncMemoryWorker:
    """
    异步记忆管线:
        - add() → 立刻返回 (非阻塞)
        - _worker() → 后台线程提取事实 → 存储
        - 失败不影响主请求
    """

    def __init__(self, memory, max_queue: int = 1000):
        self.memory = memory
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue)
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._stats = {"processed": 0, "errors": 0, "last_run": ""}

    def start(self):
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._running = False
        self._queue.put(None)  # Sentinel

    def add(self, key: str, value: str, metadata: dict = None) -> None:
        """非阻塞添加记忆"""
        try:
            self._queue.put_nowait({"key": key, "value": value, "meta": metadata or {}})
        except queue.Full:
            self._stats["errors"] += 1  # Queue full, drop silently

    def _worker(self):
        """后台工作线程"""
        while self._running:
            try:
                item = self._queue.get(timeout=1)
                if item is None:
                    break

                # Extract facts
                facts = self._extract_facts(item["value"])

                # Store in memory
                if self.memory and hasattr(self.memory, "update_memory"):
                    for fact in facts:
                        self.memory.update_memory(item["key"], fact)

                self._stats["processed"] += 1
                self._stats["last_run"] = time.strftime("%H:%M:%S")

            except queue.Empty:
                continue
            except Exception:
                self._stats["errors"] += 1

    def _extract_facts(self, text: str) -> list[str]:
        """简单事实提取（可升级为 LLM 提取）"""
        facts = []
        if len(text) > 20:
            facts.append(text[:200])
        return facts

    def stats(self) -> dict:
        return dict(self._stats)


class MemoryForgetting:
    """
    记忆遗忘机制 — Zep · Mem0 生产模式

    Three strategies:
        1. TTL on Episodic: 原始事件 30-90 天自动清理
        2. Provenance on Semantic: 每条事实标注来源, 冲突时 LLM Judge
        3. Confidence Decrement: 技能版本化, 失败扣分, 低于阈值退役
    """

    def __init__(self, ttl_days: int = 90):
        self.ttl_seconds = ttl_days * 86400
        self._entries: dict[str, dict] = {}  # key → {value, timestamp, source, confidence}

    def add(self, key: str, value: str, source: str = "", confidence: float = 1.0):
        """带时效和出处的记忆写入"""
        self._entries[key] = {
            "value": value,
            "timestamp": time.time(),
            "source": source,
            "confidence": confidence,
            "version": 1,
        }

    def get(self, key: str) -> str | None:
        """获取记忆，自动过滤过期"""
        if key not in self._entries:
            return None
        entry = self._entries[key]

        # TTL check
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            del self._entries[key]
            return None

        # Confidence check
        if entry["confidence"] < 0.3:
            return None

        return entry["value"]

    def merge(self, key: str, new_value: str, source: str = ""):
        """冲突合并 — 新事实到达时"""
        if key in self._entries:
            old = self._entries[key]
            # Simple: newer always wins (can upgrade to LLM Judge)
            old["value"] = new_value
            old["source"] = f"{old['source']},{source}" if old["source"] else source
            old["timestamp"] = time.time()
            old["version"] += 1
        else:
            self.add(key, new_value, source)

    def decrement(self, key: str, penalty: float = 0.2):
        """失败扣分 — 低于阈值退役"""
        if key in self._entries:
            self._entries[key]["confidence"] -= penalty

    def cleanup(self):
        """清理过期条目"""
        now = time.time()
        expired = [k for k, v in self._entries.items() if now - v["timestamp"] > self.ttl_seconds]
        for k in expired:
            del self._entries[k]
        return len(expired)

    def stats(self) -> dict:
        return {
            "total": len(self._entries),
            "expiring": sum(1 for v in self._entries.values()
                          if time.time() - v["timestamp"] > self.ttl_seconds * 0.8),
        }
