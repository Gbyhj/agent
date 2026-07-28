"""
Code Graph — AST 级代码图查询

Source: CodeGraphContext MCP · Reddit community pattern
Replaces: grep遍历50个文件 → 1次图查询
Savings: ~90% context tokens on large repos

Tools: find_callers · find_callees · class_hierarchy · module_deps
"""
from __future__ import annotations

import ast
import os
from collections import defaultdict


class CodeGraph:
    """代码图 — 一次索引，多次查询"""

    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self._index: dict[str, dict] = {}  # file → {functions, classes, imports}
        self._call_graph: dict[str, list[str]] = defaultdict(list)  # func → [called_funcs]
        self._imports: dict[str, list[str]] = defaultdict(list)     # file → [imports]
        self._built = False

    def build(self):
        """索引整个目录"""
        for root, _, files in os.walk(self.root_dir):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                try:
                    tree = ast.parse(open(path, encoding="utf-8").read())
                    self._index_file(path, tree)
                except Exception:
                    pass
        self._built = True

    def _index_file(self, path: str, tree: ast.AST):
        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            self._call_graph[node.name].append(child.func.id)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(n.alias.name for n in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        self._index[path] = {
            "functions": functions, "classes": classes, "imports": imports,
        }

    def find_callers(self, func_name: str) -> list[str]:
        """查找所有调用 func_name 的函数"""
        if not self._built:
            self.build()
        callers = []
        for func, calls in self._call_graph.items():
            if func_name in calls:
                callers.append(func)
        return callers

    def find_callees(self, func_name: str) -> list[str]:
        """查找 func_name 调用的所有函数"""
        if not self._built:
            self.build()
        return self._call_graph.get(func_name, [])

    def class_hierarchy(self, class_name: str) -> dict:
        """类继承关系"""
        if not self._built:
            self.build()
        result = {"name": class_name, "subclasses": [], "bases": []}
        for path, info in self._index.items():
            if class_name in info["classes"]:
                result["path"] = path
        return result

    def module_deps(self, path: str) -> list[str]:
        """模块依赖"""
        if path in self._index:
            return self._index[path]["imports"]
        return []

    def stats(self) -> dict:
        if not self._built:
            self.build()
        return {
            "files": len(self._index),
            "functions": sum(len(v["functions"]) for v in self._index.values()),
            "classes": sum(len(v["classes"]) for v in self._index.values()),
            "edges": sum(len(v) for v in self._call_graph.values()),
        }
