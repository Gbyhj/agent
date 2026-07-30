"""A2A AgentCard — 对标 Google A2A v1.0 协议

AgentCard 是 A2A 的发现机制: 每个 Agent 在 /.well-known/agent-card.json
发布自己的身份、能力和安全要求。
"""
import json, os
from dataclasses import dataclass, field, asdict

@dataclass
class AgentSkill:
    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    input_modes: list[str] = field(default_factory=lambda: ["text/plain"])
    output_modes: list[str] = field(default_factory=lambda: ["text/plain"])

@dataclass  
class AgentCard:
    """A2A Agent 身份卡 — v1.0 兼容"""
    name: str = "agent"
    description: str = "Autonomous AI Agent"
    version: str = "5.0.0"
    url: str = "http://localhost:5000/a2a"
    protocol_versions: list[str] = field(default_factory=lambda: ["1.0"])
    capabilities: dict = field(default_factory=lambda: {
        "streaming": True,
        "pushNotifications": False,
    })
    skills: list[AgentSkill] = field(default_factory=list)
    security_schemes: dict = field(default_factory=lambda: {
        "bearer": {"type": "http", "scheme": "bearer"}
    })
    
    def add_skill(self, skill_id: str, name: str, desc: str):
        self.skills.append(AgentSkill(id=skill_id, name=name, description=desc))
    
    def to_json(self) -> str:
        data = asdict(self)
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def publish(self, directory: str = "."):
        """发布到 .well-known/agent-card.json"""
        well_known = os.path.join(directory, ".well-known")
        os.makedirs(well_known, exist_ok=True)
        path = os.path.join(well_known, "agent-card.json")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        return path

def create_default_card() -> AgentCard:
    """生成默认 AgentCard"""
    card = AgentCard(
        name="agent-cli",
        description="Autonomous AI coding agent — code review, architecture analysis, search, DB design",
        url="https://agent.保康.top/a2a",
    )
    card.add_skill("code_review", "代码审查", "Review code for security, performance, and quality issues")
    card.add_skill("architecture", "架构分析", "Analyze project architecture and module dependencies")
    card.add_skill("db_design", "数据库设计", "Design database schemas with indexes and constraints")
    card.add_skill("web_search", "联网搜索", "Search for latest information and frameworks")
    return card
