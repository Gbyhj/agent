"""
Conversation Export — 对话导出为 Markdown + JSON

用法:
    from agent.tools.export import ConversationExporter
    exporter = ConversationExporter()
    exporter.export_markdown(session_id, state)
"""
from __future__ import annotations

import os
import json
from datetime import datetime


class ConversationExporter:
    """对话导出器"""

    def __init__(self, output_dir: str = "./conversations"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_markdown(self, session_id: str, task: str, messages: list,
                        tool_calls: list, final_answer: str) -> str:
        """导出为 Markdown 格式"""
        now = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{now}_{session_id[:8]}.md"
        filepath = os.path.join(self.output_dir, filename)

        lines = [
            f"# Agent 对话记录",
            f"",
            f"- **会话**: {session_id}",
            f"- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- **任务**: {task}",
            f"- **工具调用**: {len(tool_calls)} 次",
            f"",
            f"---",
            f"",
            f"## 任务",
            f"",
            f"> {task}",
            f"",
        ]

        # 对话历史
        if messages or tool_calls:
            lines.append("## 执行过程")
            lines.append("")
            for msg in messages[-30:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                name = msg.get("name", "")

                if role == "user":
                    lines.append(f"**👤 用户**: {content}")
                elif role == "assistant":
                    short = content[:200].replace("\n", " ")
                    lines.append(f"**🤖 Agent**: {short}")
                elif role == "tool":
                    short = str(content)[:150].replace("\n", " ")
                    lines.append(f"**🔧 {name}**: {short}")
                lines.append("")

        # 工具调用汇总
        if tool_calls:
            lines.append("## 工具调用汇总")
            lines.append("")
            lines.append("| 工具 | 结果 |")
            lines.append("|------|------|")
            for tc in tool_calls[-20:]:
                name = tc.get("tool", "?")
                result = str(tc.get("result", ""))[:100].replace("\n", " ")
                lines.append(f"| {name} | {result} |")
            lines.append("")

        # 最终结果
        lines.append("## 最终结果")
        lines.append("")
        lines.append(final_answer)
        lines.append("")
        lines.append("---")
        lines.append(f"*由 Agent v5 自动生成*")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filepath

    def export_json(self, session_id: str, task: str, messages: list,
                    tool_calls: list, final_answer: str, turns: int) -> str:
        """导出为 JSON 格式"""
        now = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"{now}_{session_id[:8]}.json"
        filepath = os.path.join(self.output_dir, filename)

        data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "turns": turns,
            "tool_calls_count": len(tool_calls),
            "messages": messages[-30:],
            "tool_calls": tool_calls[-30:],
            "final_answer": final_answer,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def list_exports(self) -> list[str]:
        """列出所有导出文件"""
        if not os.path.isdir(self.output_dir):
            return []
        return sorted(
            [f for f in os.listdir(self.output_dir) if f.endswith((".md", ".json"))],
            reverse=True,
        )[:20]
