"""
Work-Order Prompt — 结构化任务模板

Source: Claude Code Guides · SurePrompts
Pattern: GOAL → SCOPE → CONSTRAINTS → ACCEPTANCE → STOP
vs traditional "Please optimize my code" → ambiguous

Structure:
    ## GOAL
    What to achieve
    
    ## SCOPE  
    Files to touch / NOT touch
    
    ## CONSTRAINTS
    Rules to follow
    
    ## ACCEPTANCE
    How to verify success
    
    ## STOP
    When to stop
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WorkOrder:
    goal: str
    scope_files: list[str] = None     # Files to touch
    exclude_files: list[str] = None   # Files NOT to touch
    constraints: list[str] = None     # Rules
    acceptance: str = ""              # Verification
    stop_condition: str = "Task completed and verified"
    max_turns: int = 10

    def to_prompt(self) -> str:
        """Generate Work-Order style prompt"""
        parts = []

        parts.append(f"## GOAL\n{self.goal}")

        scope = self.scope_files or []
        if scope:
            parts.append(f"\n## SCOPE\nOnly modify: {', '.join(scope)}")
        if self.exclude_files:
            parts.append(f"Do NOT touch: {', '.join(self.exclude_files)}")

        if self.constraints:
            parts.append(f"\n## CONSTRAINTS\n" + "\n".join(f"- {c}" for c in self.constraints))

        parts.append(f"\n## ACCEPTANCE\n{self.acceptance or 'All existing tests pass. No new errors introduced.'}")

        parts.append(f"\n## STOP\n{self.stop_condition}")

        parts.append(f"\n---\nBefore starting, if unclear about any part, ask clarifying questions.")

        return "\n".join(parts)

    @staticmethod
    def from_user_input(text: str) -> WorkOrder:
        """Parse user input into Work-Order"""
        # Simple heuristic: extract key info
        goal = text
        scope_files = []
        constraints = []
        acceptance = "Tests pass. Output is correct."

        # Detect file mentions
        import re
        files = re.findall(r'[a-zA-Z0-9_/.-]+\.(py|js|ts|go|rs|java|md|html|css|yaml|toml)', text)
        if files:
            scope_files = files[:5]

        # Detect constraints
        if "不改" in text or "不要" in text or "not" in text.lower():
            constraints.append("Do not add new dependencies")
            constraints.append("Do not change public API")

        return WorkOrder(
            goal=goal,
            scope_files=scope_files,
            constraints=constraints,
            acceptance=acceptance,
        )


def build_work_order(task: str, context: dict = None) -> str:
    """Quick helper: task → Work-Order prompt"""
    wo = WorkOrder.from_user_input(task)
    if context:
        wo.acceptance = context.get("acceptance", wo.acceptance)
        wo.constraints.extend(context.get("constraints", []))
    return wo.to_prompt()
