"""
Web Search Tool — 免费 DuckDuckGo 搜索

不需要 API key，零成本让 Agent 上网搜索。

用法:
    from agent.tools.web_search import WebSearchTool
    tool = WebSearchTool()
    result = tool.execute(query="2026 AI Agent 开源项目")
"""
from __future__ import annotations

import re
import urllib.request
import urllib.parse
import json

from ..core.tool_registry import BaseTool, ToolParam


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "搜索互联网获取最新信息。适用于需要实时数据、新闻、文档的场景。"
    parameters = [
        ToolParam("query", "string", "搜索关键词", required=True),
        ToolParam("max_results", "integer", "最大结果数（默认5）"),
    ]

    def execute(self, query: str, max_results: int = 5) -> str:
        """DuckDuckGo Instant Answer API — 免费，无需 API key"""
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = []

            # Abstract（直接答案）
            if data.get("Abstract"):
                results.append(f"📌 {data['Abstract']}\n  来源: {data.get('AbstractURL', '')}")

            # Related Topics
            topics = data.get("RelatedTopics", [])
            count = 0
            for topic in topics:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"{count+1}. {topic['Text']}")
                    if topic.get("FirstURL"):
                        results.append(f"   {topic['FirstURL']}")
                    count += 1
                    if count >= max_results:
                        break

            if not results:
                # 回退：纯文本搜索
                return self._text_search(query, max_results)

            return f"搜索 '{query}':\n" + "\n".join(results)

        except Exception as e:
            return f"搜索失败: {e}\n试试更具体的关键词，或检查网络连接。"

    def _text_search(self, query: str, n: int = 5) -> str:
        """纯文本搜索回退"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # 提取搜索结果
            snippets = re.findall(r'class="result__snippet">(.+?)</a>', html, re.DOTALL)
            results = []
            for i, s in enumerate(snippets[:n]):
                text = re.sub(r"<[^>]+>", "", s).strip()
                results.append(f"{i+1}. {text[:200]}")

            return f"搜索 '{query}':\n" + "\n".join(results) if results else f"未找到 '{query}' 的相关结果。"

        except Exception:
            return f"搜索 '{query}' 暂时不可用。"
