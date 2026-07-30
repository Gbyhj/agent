"""Agent SOUL.md — OpenClaw 模式: 可写身份文件, 每次启动读取自己"""
import os, time, json

SOUL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SOUL.md")

class Soul:
    """持久化 Agent 身份 — 对标 OpenClaw 125K⭐ 的核心原语
    
    每次 Agent 启动时读取 SOUL.md 定义"我是谁"。
    Agent 可以建议修改 SOUL.md, 但需用户确认 (Human-in-the-loop)。
    """
    
    def __init__(self, path: str = None):
        self.path = path or SOUL_PATH
        self._ensure_exists()
        self.identity = self._load()
    
    def _ensure_exists(self):
        if not os.path.exists(self.path):
            default = """# Agent SOUL — 核心身份
## 我是谁
我是一个自主 AI 助手, 专注于代码审查、架构分析和信息检索。

## 我的价值观
- 准确性优先于速度
- 安全第一, 不可逆操作需确认
- 透明沟通, 不确定时说明
- 持续学习, 从每次交互中改进

## 我的风格
- 简洁直接
- 代码优先, 解释按需
- 用中文回答中文问题

## 行为边界
- 不修改自身 SOUL.md 除非用户明确要求
- 不绕过安全检查
- 不执行危险命令
"""
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write(default)
    
    def _load(self) -> dict:
        with open(self.path, encoding='utf-8') as f:
            content = f.read()
        return {
            "raw": content,
            "mtime": os.path.getmtime(self.path),
            "tokens_est": len(content) // 4,  # rough estimate
        }
    
    def get_prompt(self) -> str:
        """获取注入到 System Prompt 的身份上下文"""
        return f"""[IDENTITY — 只读, 定义你是谁]
{self.identity['raw']}
[/IDENTITY]
"""
    
    def propose_change(self, section: str, new_content: str) -> str:
        """Agent 建议修改身份, 返回 diff 供用户审批"""
        old = self.identity['raw']
        # Find section boundary
        marker = f"## {section}"
        idx = old.find(marker)
        if idx < 0:
            return f"[REJECTED] Section '{section}' not found in SOUL.md"
        
        # Generate proposal (保存到 .agent/proposals/)
        proposal_dir = os.path.join(os.path.dirname(self.path), "proposals")
        os.makedirs(proposal_dir, exist_ok=True)
        proposal_path = os.path.join(proposal_dir, f"soul_{int(time.time())}.md")
        
        with open(proposal_path, 'w', encoding='utf-8') as f:
            f.write(f"# SOUL Change Proposal\n\n## Affected Section\n{section}\n\n## Current\n```\n{old[idx:idx+200]}...\n```\n\n## Proposed\n```\n{new_content}\n```\n")
        
        return f"[PENDING APPROVAL] Proposal saved to {proposal_path}\nAction: review and confirm to apply"

    def apply_change(self, section: str, new_content: str) -> bool:
        """应用已批准的修改"""
        try:
            old = open(self.path, encoding='utf-8').read()
            marker = f"## {section}"
            idx = old.find(marker)
            if idx < 0: return False
            # Replace section content until next ## or EOF
            end = old.find("\n##", idx + len(marker))
            if end < 0: end = len(old)
            updated = old[:idx+len(marker)] + "\n" + new_content + old[end:]
            open(self.path, 'w', encoding='utf-8').write(updated)
            self.identity = self._load()
            return True
        except Exception:
            return False
    
    def evolve_from_experience(self, lesson: str):
        """从经验中学习 — 记录到 '经验教训' 节 (对标 SelfEvolve)"""
        old = open(self.path, encoding='utf-8').read()
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        entry = f"\n- [{timestamp}] {lesson}"
        
        if "## 经验教训" not in old:
            old += "\n\n## 经验教训\n" + entry
        else:
            old = old.replace("## 经验教训", f"## 经验教训\n{entry}")
        
        open(self.path, 'w', encoding='utf-8').write(old)
        self.identity = self._load()
