"""Prompt Caching Optimizer — Static-First 排序

规则:
  1. Static-First: 系统→工具→few-shot→历史→最新(从不)打破顺序
  2. 字节匹配: 不变内容永远在前面, 动态内容只在末尾
  3. Cache Breakpoints: 标记4个缓存点

收益: 90% token折扣 (Anthropic) / 50% (OpenAI)
"""
class PromptCacheOptimizer:
    """构建缓存友好的 System Prompt"""
    
    @staticmethod
    def build(system_prompt: str, tools_schema: str, 
              examples: str, history: str, user_msg: str) -> dict:
        """按 Static-First 顺序组装, 返回缓存点标记"""
        blocks = []
        
        # Breakpoint 1: System Prompt (最大缓存价值)
        blocks.append({"type": "system", "cache": True, "content": system_prompt})
        
        # Breakpoint 2: Tool Definitions (会话内固定)
        blocks.append({"type": "tools", "cache": True, "content": tools_schema})
        
        # Breakpoint 3: Few-shot Examples
        if examples:
            blocks.append({"type": "examples", "cache": True, "content": examples})
        
        # Breakpoint 4: Conversation History (增长但前端固定)
        if history:
            blocks.append({"type": "history", "cache": True, "content": history})
        
        # NEVER cache: User message (always dynamic)
        blocks.append({"type": "user", "cache": False, "content": user_msg})
        
        return {"blocks": blocks, "cache_hit_rate": "est. 70-90%"}
    
    @staticmethod
    def audit(prompt_parts: list[str]) -> dict:
        """审计 Prompt 是否破坏缓存"""
        warnings = []
        # Check: 动态内容是否出现在静态内容之前
        for i, part in enumerate(prompt_parts[:-1]):
            if any(dyn in part for dyn in ["timestamp", "request_id", "session_"]):
                warnings.append(f"Dynamic content at position {i} will invalidate all subsequent cache")
        return {"warnings": warnings, "optimized": len(warnings) == 0}
