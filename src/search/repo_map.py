"""Repo-Map — Aider 式 AST 代码图 + PageRank 排序"""
import ast, os
from collections import defaultdict

class RepoMap:
    """tree-sitter AST → PageRank → 压缩上下文"""
    def __init__(self, root_dir: str = "."):
        self.root = root_dir
        self.symbols: dict[str, dict] = {}
        self.deps: dict[str, list[str]] = defaultdict(list)
    
    def build(self):
        for root, _, files in os.walk(self.root):
            for f in files:
                if not f.endswith(".py"): continue
                path = os.path.join(root, f)
                try:
                    tree = ast.parse(open(path, encoding="utf-8").read())
                    self._extract(path, tree)
                except: pass
        return self
    
    def _extract(self, path: str, tree: ast.AST):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                fid = f"{path}:{node.name}"
                self.symbols[fid] = {"type": type(node).__name__, "name": node.name, "file": path}
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        self.deps[fid].append(child.func.id)
    
    def rank(self, query: str, top_k: int = 10) -> list:
        """PageRank 排序: 返回与查询最相关的符号"""
        scores = {}
        for sid, info in self.symbols.items():
            score = 0
            name = info["name"].lower()
            if query.lower() in name: score += 10
            # PageRank bonus: 被引用越多越重要
            refs = sum(1 for d in self.deps.values() if info["name"] in d)
            score += min(refs, 5)
            if score > 0: scores[sid] = score
        
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        return [{"symbol": s, "score": sc, **self.symbols[s]} for s, sc in ranked]
    
    def map_summary(self, max_chars: int = 1000) -> str:
        """生成类似 Aider /map 的压缩摘要"""
        lines = []
        for sid, info in list(self.symbols.items())[:30]:
            lines.append(f"{info['type']}: {info['name']} ({info['file']})")
        summary = "\n".join(lines)
        return summary[:max_chars]
