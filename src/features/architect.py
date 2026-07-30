"""Architect/Editor 模式 — Aider/Sweep 双模型分工

Architect (推理模型): 分析任务 · 制定计划 · 分解步骤
Editor (编辑模型):   按计划执行 · 生成代码 · 应用变更

收益: +10分 benchmark (Aider Polyglot), 成本降低50%
"""
class ArchitectEditor:
    """双模型分工: 规划用强模型, 执行用便宜模型"""
    def __init__(self, architect_llm=None, editor_llm=None):
        self.architect = architect_llm
        self.editor = editor_llm
    
    def solve(self, task: str, context: dict = None) -> dict:
        """Architect → Editor 两阶段"""
        # Phase 1: Architect plans
        plan = self._plan(task, context or {})
        
        # Phase 2: Editor executes
        result = self._execute(plan, task)
        
        return {"plan": plan, "result": result, "method": "architect/editor"}
    
    def _plan(self, task: str, context: dict) -> str:
        if self.architect:
            prompt = f"规划任务: {task}\n上下文: {context}\n输出: 有序步骤列表"
            resp = self.architect.chat([{"role":"user","content":prompt}])
            return resp.content[:2000] if hasattr(resp,'content') else str(resp)[:500]
        return f"Step 1: 分析{task[:30]}...\nStep 2: 实现\nStep 3: 验证"
    
    def _execute(self, plan: str, task: str) -> str:
        if self.editor:
            prompt = f"按计划执行: {plan[:500]}\n任务: {task}"
            resp = self.editor.chat([{"role":"user","content":prompt}])
            return resp.content[:2000] if hasattr(resp,'content') else str(resp)[:500]
        return f"执行完成: {task[:50]}"
