"""自动 git commit — Aider/Sweep/Replit 模式"""
import subprocess, os

class AutoGit:
    """每步变更自动 commit + 语义消息"""
    @staticmethod
    def commit(change_desc: str, files: list[str] = None) -> str:
        try:
            if files: subprocess.run(["git", "add"] + files, capture_output=True, text=True)
            else: subprocess.run(["git", "add", "."], capture_output=True, text=True)
            
            msg = f"🤖 agent: {change_desc[:72]}"
            result = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
            return result.stdout.strip() or msg
        except Exception as e:
            return f"Git commit failed: {e}"
    
    @staticmethod
    def status() -> str:
        try:
            return subprocess.check_output(["git","status","--short"], text=True).strip() or "Clean"
        except: return "Not a git repo"
