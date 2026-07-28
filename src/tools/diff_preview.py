"""
Diff Preview Tool — Cline 式变更预览

参考 Cline: 写文件前先展示 diff，用户确认后才写入。
"""
from __future__ import annotations

import os
import difflib


class DiffPreview:
    """文件变更预览"""

    @staticmethod
    def preview(filepath: str, new_content: str, context_lines: int = 3) -> str:
        """比较旧内容和新内容，返回彩色 diff"""
        if not os.path.exists(filepath):
            return f"[New] {filepath}\n+{len(new_content)} lines to create"

        with open(filepath, encoding="utf-8") as f:
            old_content = f.read()

        if old_content == new_content:
            return f"[No changes] {filepath}"

        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            n=context_lines,
        )
        result = "".join(diff)

        lines = new_content.count("\n") - old_content.count("\n")
        summary = f"[Diff] {filepath}: {len(result)} chars, net {lines:+d} lines"

        return f"{summary}\n{result}"

    @staticmethod
    def confirm(self, filepath: str, new_content: str) -> tuple[bool, str]:
        """返回 (是否确认写入, diff预览)"""
        preview = self.preview(filepath, new_content)
        return True, preview  # 默认确认（可替换为交互式确认）
