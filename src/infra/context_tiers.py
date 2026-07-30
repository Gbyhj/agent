"""L1/L2/L3 上下文分层 — Context Doctor 模式

L1 — Always-on:  系统指令, 关键规则    (~2-5K tokens)
L2 — Session:    当前任务状态, 决策记录  (~5-20K tokens)  
L3 — On-demand:  参考资料, 仅需时加载   (unbounded)

规则: 
  - L1 在最前面和最后面 (首尾效应)
  - L2 在 L1 和 L3 之间
  - L3 从不混入 L1/L2, 用完后清除
  - 工具结果消费后立即从 L2 清除
"""
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

@dataclass
class ContextTier:
    """三层上下文管理器 — 对标 Claude 5 Context Doctor"""
    
    l1_always: list[str] = field(default_factory=list)      # 系统 · 核心规则
    l2_session: list[str] = field(default_factory=list)      # 任务 · 决策 · 工具结论
    l3_reference: list[str] = field(default_factory=list)    # 文档 · 历史 · 研究
    _token_counter: Optional[Callable] = None
    
    def add_l1(self, content: str, tag: str = ""):
        """添加到始终在线的 L1 层"""
        prefix = f"[{tag}] " if tag else ""
        self.l1_always.append(f"{prefix}{content}")
    
    def add_l2(self, content: str, source: str = ""):
        """添加到会话层 (任务状态/决策/工具结论)"""
        prefix = f"[{source}] " if source else ""
        self.l2_session.append(f"{prefix}{content}")
    
    def add_l3(self, content: str, key: str = ""):
        """添加到按需加载层"""
        self.l3_reference.append(f"[{key}] {content}")
    
    def clear_tool_results(self, source: str = ""):
        """消费后清除工具原始输出, 只留结论 (减半上下文)"""
        if source:
            self.l2_session = [l for l in self.l2_session if f"[{source}]" not in l]
        else:
            # Clear last tool output
            if self.l2_session:
                self.l2_session.pop()
    
    def compact_l2(self, llm=None, max_items: int = 20):
        """压缩 L2 层: 超过阈值时汇总旧条目"""
        if len(self.l2_session) <= max_items:
            return
        
        # 保留最近 N 条, 压缩更早的
        old = self.l2_session[:-max_items]
        recent = self.l2_session[-max_items:]
        
        summary = "【会话摘要】" + " · ".join(
            item[:80] for item in old[-10:]  # last 10 old items
        )
        self.l2_session = [summary] + recent
    
    def assert_critical_rule(self, rule: str):
        """确保关键规则在 L1 中出现 (不会因压缩丢失)"""
        if rule not in "\n".join(self.l1_always):
            self.l1_always.append(rule)
    
    def build(self, max_tokens: int = 8000) -> str:
        """构建最终上下文: L1 首尾 + L2 + L3 (如空间允许)"""
        parts = []
        
        # L1 — always at the top (primacy effect)
        l1_text = "\n".join(self.l1_always)
        parts.append(l1_text)
        
        # L2 — session state
        l2_text = "\n".join(self.l2_session)
        parts.append(l2_text)
        
        # L3 — on-demand, only if space
        leftover = max_tokens - (len(l1_text) + len(l2_text)) // 4
        if leftover > 500 and self.l3_reference:
            l3_items = self.l3_reference[: max(1, leftover // 100)]
            parts.append("【参考资料】\n" + "\n".join(l3_items))
        
        # L1 repeat — at the end (recency effect)
        parts.append(l1_text)
        
        built = "\n\n".join(parts)
        
        # Audit: warn if too large
        est_tokens = len(built) // 4
        if est_tokens > max_tokens:
            from ..shared.logger import log
            log.warn(f"Context exceeds budget: {est_tokens}/{max_tokens} tokens")
        
        return built
    
    def stats(self) -> dict:
        return {
            "l1_items": len(self.l1_always),
            "l2_items": len(self.l2_session),
            "l3_items": len(self.l3_reference),
            "est_tokens": len(self.build()) // 4,
            "tool_consumed": True,
        }
