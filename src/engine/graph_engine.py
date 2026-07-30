"""Graph Engineering — 对标 Steinberger 2026 核心范式

"Loops make agent behavior programmable. Graphs make agent organizations programmable."

两层图:
  Org Graph (稳定):  长期Agent组织 · 角色 · 领域所有权 · 持久记忆
  Work Graph (动态): 当前任务编排 · 可分裂/合并/重排/消失
  
核心创新: Work Graph 在运行时自修改。
"""
import time, json, os
from dataclasses import dataclass, field
from enum import Enum

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class OrgNode:
    """Org Graph 节点 — 长期Agent身份"""
    id: str
    role: str
    domain: str          # 领域所有权
    tools: list[str] = field(default_factory=list)
    memory_keys: list[str] = field(default_factory=list)
    status: str = "active"

@dataclass
class WorkNode:
    """Work Graph 节点 — 动态任务"""
    id: str
    task: str
    status: NodeStatus = NodeStatus.PENDING
    dependencies: list[str] = field(default_factory=list)   # 前置节点ID
    assigned_to: str = ""     # OrgNode ID
    result: str = ""
    created: float = 0.0
    priority: int = 5          # 1-10, 10最高
    
    def __post_init__(self):
        if not self.created: self.created = time.time()

@dataclass
class WorkEdge:
    """Work Graph 边 — 数据流依赖"""
    from_node: str
    to_node: str
    data_type: str = "result"   # result | context | approval

class GraphEngine:
    """双层图引擎 — 对标 Steinberger 的 Graph Engineering"""
    
    def __init__(self):
        # Org Graph (稳定)
        self.org: dict[str, OrgNode] = {}
        # Work Graph (动态, 每个任务周期重建)
        self.work_nodes: dict[str, WorkNode] = {}
        self.work_edges: list[WorkEdge] = []
        self._node_counter = 0
        self._execution_log: list[dict] = []
    
    # ── Org Graph ──
    def add_role(self, role_id: str, role: str, domain: str, tools: list[str] = None):
        """注册长期Agent角色 (对标 Org Graph 稳定节点)"""
        self.org[role_id] = OrgNode(
            id=role_id, role=role, domain=domain,
            tools=tools or []
        )
    
    def get_role(self, role_id: str) -> OrgNode | None:
        return self.org.get(role_id)
    
    def list_roles(self) -> list[dict]:
        return [{"id": n.id, "role": n.role, "domain": n.domain, "status": n.status}
                for n in self.org.values()]
    
    # ── Work Graph ──
    def create_work_node(self, task: str, dependencies: list[str] = None,
                         assigned_role: str = "", priority: int = 5) -> str:
        """创建动态任务节点 (Work Graph)"""
        self._node_counter += 1
        nid = f"task_{self._node_counter}"
        self.work_nodes[nid] = WorkNode(
            id=nid, task=task, 
            dependencies=dependencies or [],
            assigned_to=assigned_role,
            priority=priority
        )
        return nid
    
    def add_edge(self, from_id: str, to_id: str, data_type: str = "result"):
        """添加数据流依赖边"""
        if from_id in self.work_nodes and to_id in self.work_nodes:
            self.work_edges.append(WorkEdge(from_node=from_id, to_node=to_id, data_type=data_type))
            # 自动添加依赖
            node = self.work_nodes[to_id]
            if from_id not in node.dependencies:
                node.dependencies.append(from_id)
    
    def split_node(self, node_id: str, subtasks: list[str]) -> list[str]:
        """分裂节点 — Work Graph 自修改能力 (对标 Steinberger)"""
        if node_id not in self.work_nodes:
            return []
        
        original = self.work_nodes[node_id]
        original.status = NodeStatus.CANCELLED
        original.result = f"Split into {len(subtasks)} subtasks"
        
        new_ids = []
        for i, task in enumerate(subtasks):
            nid = self.create_work_node(
                task=task,
                dependencies=original.dependencies.copy(),
                assigned_role=original.assigned_to,
                priority=original.priority
            )
            new_ids.append(nid)
        
        # 更新依赖: 所有依赖原节点的 → 依赖所有新节点
        for edge in self.work_edges:
            if edge.from_node == node_id:
                for nid in new_ids:
                    self.add_edge(nid, edge.to_node, edge.data_type)
        
        self._execution_log.append({
            "action": "split", "node": node_id, 
            "into": new_ids, "reason": "complexity discovered at runtime"
        })
        return new_ids
    
    def merge_nodes(self, node_ids: list[str], new_task: str) -> str:
        """合并节点 — 范围变更时动态重组"""
        for nid in node_ids:
            if nid in self.work_nodes:
                self.work_nodes[nid].status = NodeStatus.CANCELLED
        
        merged = self.create_work_node(task=new_task)
        self._execution_log.append({
            "action": "merge", "nodes": node_ids, 
            "into": merged, "reason": "scope changed"
        })
        return merged
    
    def cancel_if_unnecessary(self, node_id: str, reason: str):
        """因证据发现任务不必要而取消"""
        if node_id in self.work_nodes:
            self.work_nodes[node_id].status = NodeStatus.CANCELLED
            self.work_nodes[node_id].result = f"Cancelled: {reason}"
            self._execution_log.append({
                "action": "cancel", "node": node_id, "reason": reason
            })
    
    def reorder_by_priority(self):
        """按优先级重排 — Work Graph 自适应"""
        self._execution_log.append({"action": "reorder"})
    
    # ── 可执行节点 ──
    def get_ready_nodes(self) -> list[WorkNode]:
        """返回所有就绪节点 (依赖已完成)"""
        ready = []
        for node in self.work_nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            deps_met = all(
                self.work_nodes.get(d) and self.work_nodes[d].status == NodeStatus.COMPLETED
                for d in node.dependencies
            )
            if deps_met:
                ready.append(node)
        
        # Sort by priority descending
        ready.sort(key=lambda n: -n.priority)
        return ready
    
    def complete_node(self, node_id: str, result: str):
        if node_id in self.work_nodes:
            self.work_nodes[node_id].status = NodeStatus.COMPLETED
            self.work_nodes[node_id].result = result
    
    def fail_node(self, node_id: str, error: str):
        if node_id in self.work_nodes:
            self.work_nodes[node_id].status = NodeStatus.FAILED
            self.work_nodes[node_id].result = error
    
    # ── 可视化 ──
    def to_mermaid(self) -> str:
        """生成 Mermaid 图 (Org Graph + Work Graph)"""
        lines = ["graph TD"]
        
        # Org nodes
        for n in self.org.values():
            lines.append(f"    {n.id}[({n.role}) {n.domain}]")
        
        # Work nodes with status colors
        for n in self.work_nodes.values():
            style = {
                NodeStatus.PENDING: "",
                NodeStatus.RUNNING: ":::running",
                NodeStatus.COMPLETED: ":::done",
                NodeStatus.FAILED: ":::failed",
                NodeStatus.CANCELLED: ":::cancelled",
            }.get(n.status, "")
            lines.append(f"    {n.id}[{n.task[:30]}]{style}")
        
        # Edges
        for e in self.work_edges:
            lines.append(f"    {e.from_node} -->|{e.data_type}| {e.to_node}")
        
        return "\n".join(lines)
    
    def summary(self) -> dict:
        return {
            "org_roles": len(self.org),
            "work_nodes": {
                "total": len(self.work_nodes),
                "pending": sum(1 for n in self.work_nodes.values() if n.status == NodeStatus.PENDING),
                "running": sum(1 for n in self.work_nodes.values() if n.status == NodeStatus.RUNNING),
                "completed": sum(1 for n in self.work_nodes.values() if n.status == NodeStatus.COMPLETED),
                "failed": sum(1 for n in self.work_nodes.values() if n.status == NodeStatus.FAILED),
                "cancelled": sum(1 for n in self.work_nodes.values() if n.status == NodeStatus.CANCELLED),
            },
            "edges": len(self.work_edges),
            "graph_mutations": len(self._execution_log),
        }

# ── 预设团队模板 ──
def create_default_org() -> GraphEngine:
    """创建默认 Agent 组织 (对标 Steinberger 的 Org Graph)"""
    ge = GraphEngine()
    ge.add_role("researcher", "研究员", "信息检索", ["web_search", "grep", "read_file"])
    ge.add_role("architect", "架构师", "系统设计", ["analyze_deps", "design_patterns"])
    ge.add_role("coder", "开发者", "代码实现", ["write_file", "edit_file", "run_test"])
    ge.add_role("reviewer", "审查者", "质量保证", ["review_code", "security_scan", "run_benchmark"])
    return ge
