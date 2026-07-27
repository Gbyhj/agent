"""
内置工具集 — File / Search / Shell / Web

参考实现:
- Grok Build: ReadFileTool, SearchReplaceTool, GrepTool, BashTool, WebFetchTool
- Smolagents: DuckDuckGoSearchTool, WebSearchTool, PythonInterpreterTool
- Browser-Use: Playwright 驱动的浏览器工具
"""
from __future__ import annotations

import os
import re
import glob
import subprocess
from dataclasses import dataclass, field

from ..core.tool_registry import BaseTool, ToolParam, tool


# ── 文件操作工具 ──────────────────────────────────
class ReadFileTool(BaseTool):
    name = "read_file"
    description = "读取指定文件内容。支持行号范围。"
    parameters = [
        ToolParam("path", "string", "文件路径（绝对或相对）", required=True),
        ToolParam("start_line", "integer", "起始行（1-based）"),
        ToolParam("end_line", "integer", "结束行（1-based）"),
    ]

    def execute(self, path: str, start_line: int = 1, end_line: int | None = None) -> str:
        if not os.path.exists(path):
            return f"文件不存在: {path}"
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            end = min(end_line or len(lines), len(lines))
            start = max(1, start_line)

            result_lines = []
            for i in range(start - 1, end):
                result_lines.append(f"{i+1:4d}| {lines[i].rstrip()}")

            return f"文件 {path} ({len(lines)} 行) [L{start}-L{end}]:\n" + "\n".join(result_lines)
        except Exception as e:
            return f"读取失败: {e}"


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "写入或创建文件"
    is_destructive = True
    parameters = [
        ToolParam("path", "string", "文件路径", required=True),
        ToolParam("content", "string", "文件内容", required=True),
    ]

    def execute(self, path: str, content: str) -> str:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"已写入 {path} ({len(content)} 字符)"
        except Exception as e:
            return f"写入失败: {e}"


class ListDirTool(BaseTool):
    name = "list_dir"
    description = "列出目录内容"
    parameters = [
        ToolParam("path", "string", "目录路径", required=True),
        ToolParam("pattern", "string", "文件名 glob 模式（如 *.py）"),
    ]

    def execute(self, path: str, pattern: str = "*") -> str:
        if not os.path.isdir(path):
            return f"不是目录: {path}"
        try:
            files = sorted(glob.glob(os.path.join(path, pattern)))
            items = []
            for f in files[:100]:
                name = os.path.basename(f)
                full = os.path.join(path, name)
                t = "DIR" if os.path.isdir(full) else "FILE"
                items.append(f"  [{t}] {name}")
            return f"目录 {path} ({len(files)} 项, 显示前100):\n" + "\n".join(items)
        except Exception as e:
            return f"列出失败: {e}"


# ── 搜索工具 ──────────────────────────────────────
class GrepTool(BaseTool):
    name = "grep"
    description = "在文件中搜索关键词（支持正则）"
    parameters = [
        ToolParam("pattern", "string", "搜索模式（支持正则）", required=True),
        ToolParam("path", "string", "搜索路径（文件或目录）", required=True),
        ToolParam("case_sensitive", "boolean", "是否大小写敏感"),
    ]

    def execute(self, pattern: str, path: str, case_sensitive: bool = False) -> str:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            results = []
            if os.path.isfile(path):
                files = [path]
            else:
                files = []
                for root, _, fnames in os.walk(path):
                    if any(skip in root for skip in [".git", "__pycache__", "node_modules", ".venv"]):
                        continue
                    for fname in fnames:
                        files.append(os.path.join(root, fname))
                        if len(files) >= 500:
                            break
                    if len(files) >= 500:
                        break

            for fpath in files[:200]:
                try:
                    with open(fpath, encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line, flags):
                                results.append(f"{fpath}:{i}: {line.strip()[:120]}")
                                if len(results) >= 50:
                                    break
                except Exception:
                    continue
                if len(results) >= 50:
                    break

            return f"搜索 '{pattern}':\n" + "\n".join(results[:50]) if results else f"未找到匹配 '{pattern}'"
        except Exception as e:
            return f"搜索失败: {e}"


# ── Shell 工具 ──────────────────────────────────────
class BashTool(BaseTool):
    name = "bash"
    description = "执行 Shell 命令。危险操作（rm -rf 等）会被拦截。"
    is_destructive = True
    parameters = [
        ToolParam("command", "string", "要执行的 Shell 命令", required=True),
        ToolParam("timeout", "integer", "超时（秒），默认 30"),
    ]

    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/", r"dd\s+if=", r"mkfs\.", r">\s*/dev/sd",
        r"chmod\s+777\s+/", r"sudo\s+rm", r":(){ :|:& };:"
    ]

    def execute(self, command: str, timeout: int = 30) -> str:
        # 安全检查（参考 Grok Build Bash permission gate）
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return f"拒绝执行危险命令（匹配: {pattern}）"

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=min(timeout, 120), cwd=os.getcwd()
            )
            output = result.stdout[:5000]
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr[:2000]}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return output or "(无输出)"
        except subprocess.TimeoutExpired:
            return f"命令超时 ({timeout}s)"
        except Exception as e:
            return f"执行失败: {e}"


# ── Web 工具 ──────────────────────────────────────
class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "获取网页内容"
    parameters = [
        ToolParam("url", "string", "网页 URL", required=True),
    ]

    def execute(self, url: str) -> str:
        # SSRF 防护（参考 Grok Build web_fetch/ssrf.rs）
        if url.startswith("file://") or "localhost" in url or "127.0.0.1" in url:
            return "拒绝访问本地地址"

        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "Agent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                # 简单文本提取
                content = re.sub(r"<[^>]+>", " ", content)
                content = re.sub(r"\s+", " ", content)
                return content[:5000]
        except Exception as e:
            return f"获取失败: {e}"


# ── 批量注册 ──────────────────────────────────────
def get_builtin_tools() -> list[BaseTool]:
    """获取所有内置工具（参考 Grok Build register_all()）"""
    return [
        ReadFileTool(),
        WriteFileTool(),
        ListDirTool(),
        GrepTool(),
        BashTool(),
        WebFetchTool(),
    ]
