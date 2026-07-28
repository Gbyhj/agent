"""实体图谱记忆示例"""
from agent.memory.graph_memory import GraphMemory

gm = GraphMemory()
gm.link("mem_1", [{"type": "技术", "data": "Python"}, {"type": "框架", "data": "FastAPI"}])
gm.link("mem_2", [{"type": "技术", "data": "Python"}, {"type": "数据库", "data": "PostgreSQL"}])

results = [("mem_1", 0.9), ("mem_2", 0.8), ("mem_3", 0.1)]
hybrid = gm.hybrid_search("Python 开发", results)
print(f"混合检索结果: {hybrid}")
