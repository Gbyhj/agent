"""记忆系统示例"""
from agent.memory.memory import MemorySystem

mem = MemorySystem()
mem.update_memory("用户偏好", "喜欢简洁的代码风格")
mem.update_memory("项目信息", "使用 Python 3.12 + Flask")

ctx = mem.get_context_for_llm()[:200]
print(f"记忆上下文: {ctx[:200]}")
