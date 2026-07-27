"""
Memory System — 持久化记忆

设计融合:
- OpenClaw: SOUL.md + MEMORY.md + HEARTBEAT.md Markdown 文件式记忆
- Hermes Agent: 三层记忆（长效语义/工作记忆/情景日志）
- Mem0: 向量+图谱混合检索
- ChromaDB: 轻量级向量存储

当前实现: 文件式记忆（Markdown，人类可读写，git 可版本化）
未来扩展: 接入 Mem0 / ChromaDB 做语义检索
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class MemoryConfig:
    """记忆系统配置"""
    base_dir: str = "./.agent_memory"
    soul_file: str = "SOUL.md"
    memory_file: str = "MEMORY.md"
    daily_log_dir: str = "daily"
    max_daily_log_entries: int = 50


class MemorySystem:
    """
    Agent 记忆系统

    参考 OpenClaw 的记忆架构:
    - SOUL.md: Agent 人格定义
    - MEMORY.md: 核心记忆（偏好、约定、长期知识）
    - daily/*.md: 每日工作日志（append-only）

    参考 Hermes Agent 的记忆分层:
    - 工作记忆: 当前会话上下文（在 AgentState 中管理）
    - 长效记忆: MEMORY.md 中的持久化事实
    - 情景日志: daily/*.md 每日记录
    """

    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        os.makedirs(self.config.base_dir, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self):
        """确保基础记忆文件存在"""
        soul_path = self._path(self.config.soul_file)
        mem_path = self._path(self.config.memory_file)

        if not os.path.exists(soul_path):
            with open(soul_path, "w", encoding="utf-8") as f:
                f.write("# SOUL.md — Agent 人格\n\n"
                        "- 名称: 待定义\n"
                        "- 风格: 专业、务实\n"
                        "- 原则: 先分析后行动、透明可审计\n")

        if not os.path.exists(mem_path):
            with open(mem_path, "w", encoding="utf-8") as f:
                f.write("# MEMORY.md — 核心记忆\n\n"
                        f"## 用户偏好\n(待积累)\n\n"
                        f"## 项目约定\n(待积累)\n\n"
                        f"## 已学习技能\n(待积累)\n")

    def _path(self, filename: str) -> str:
        return os.path.join(self.config.base_dir, filename)

    # ── 读写 ──────────────────────────────────────────
    def read_soul(self) -> str:
        """读取 Agent 人格定义"""
        return self._read(self.config.soul_file)

    def read_memory(self) -> str:
        """读取核心记忆"""
        return self._read(self.config.memory_file)

    def update_memory(self, key: str, value: str):
        """
        更新核心记忆（参考 OpenClaw MEMORY.md append）

        格式:
            ## key
            - value (timestamp)
        """
        mem = self.read_memory()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"- {value} ({now})\n"

        if f"## {key}" in mem:
            # 追加到已有 section
            section_start = mem.index(f"## {key}")
            next_section = mem.find("\n## ", section_start + 1)
            if next_section == -1:
                next_section = len(mem)
            mem = mem[:next_section] + entry + mem[next_section:]
        else:
            mem += f"\n## {key}\n{entry}"

        self._write(self.config.memory_file, mem)

    def log_daily(self, content: str):
        """记录每日工作日志（append-only，参考 Hermes 情景日志）"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = self._path(self.config.daily_log_dir)
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, f"{today}.md")
        timestamp = datetime.now().strftime("%H:%M")
        entry = f"\n## {timestamp}\n{content}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

        # 清理旧日志
        self._cleanup_logs(log_dir)

    def _cleanup_logs(self, log_dir: str):
        """清理超过限制的日志条目"""
        files = sorted(os.listdir(log_dir), reverse=True)
        for f in files[self.config.max_daily_log_entries:]:
            os.remove(os.path.join(log_dir, f))

    # ── 上下文注入 ─────────────────────────────────────
    def get_context_for_llm(self) -> str:
        """
        构建注入 LLM 的记忆上下文
        参考 OpenClaw 的 context assembly:
        SOUL.md → MEMORY.md → 近期日志 → 拼接
        """
        parts = []

        soul = self.read_soul()
        if soul.strip():
            parts.append(f"<soul>\n{soul}\n</soul>")

        mem = self.read_memory()
        if mem.strip():
            parts.append(f"<memory>\n{mem[:3000]}\n</memory>")  # 截断防止过长

        # 近期日志
        log_dir = self._path(self.config.daily_log_dir)
        if os.path.isdir(log_dir):
            recent_logs = sorted(os.listdir(log_dir))[-3:]  # 最近3天
            for log_file in recent_logs:
                log_content = self._read(f"daily/{log_file}")[:1000]
                if log_content.strip():
                    parts.append(f"<daily_log date='{log_file.replace('.md','')}'>\n{log_content}\n</daily_log>")

        return "\n\n".join(parts)

    # ── 内部读写 ─────────────────────────────────────
    def _read(self, filename: str) -> str:
        path = self._path(filename)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read()
        return ""

    def _write(self, filename: str, content: str):
        with open(self._path(filename), "w", encoding="utf-8") as f:
            f.write(content)
