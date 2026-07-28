"""
Reflex System — 条件反射系统

灵感: Hermes Agent 自动技能生成 × Smolagents Code-First

Agent 自动积累"条件反射"——模式→代码片段的映射库。
重复任务匹配到已知模式时，直接执行，跳过 LLM 调用。
可节省 70-90% API 费用。

用法:
    reflex = ReflexSystem()
    
    # 记录成功任务
    reflex.learn(
        pattern_keywords=["print", "改成", "logger"],
        pattern_regex=r"把 (.+) 的 print 改成 logger",
        code_template="sed -i 's/print(/logger.info(/g' {path}",
    )
    
    # 匹配任务
    result = reflex.match("把 agent/core/agent.py 的 print 改成 logger.info")
    if result:
        # 直接执行，不调 LLM
        os.system(result.code.format(path="agent/core/agent.py"))
"""
from __future__ import annotations

import os
import re
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Reflex:
    """单个条件反射"""
    id: str
    trigger_keywords: list[str]      # 触发关键词
    trigger_regex: str = ""          # 触发正则（更精确）
    code_template: str = ""          # 代码模板（支持 {var} 占位）
    description: str = ""            # 人类可读描述
    success_count: int = 0           # 成功次数
    total_saved_cost: float = 0.0    # 累计节省费用
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class ReflexSystem:
    """
    条件反射系统

    存储: ~/.agent_reflexes.json (持久化)
    
    匹配流程:
    1. 关键词匹配 → 候选集
    2. 正则精确匹配 → 最佳候选
    3. 提取变量 → 填充模板
    4. 执行 → 记录成功/失败
    """

    def __init__(self, path: str | None = None):
        self.path = path or os.path.expanduser("~/.agent_reflexes.json")
        self._reflexes: dict[str, Reflex] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                data = json.load(open(self.path, encoding="utf-8"))
                self._reflexes = {k: Reflex(**v) for k, v in data.items()}
            except Exception:
                pass

    def _save(self):
        data = {k: {
            "id": r.id, "trigger_keywords": r.trigger_keywords,
            "trigger_regex": r.trigger_regex, "code_template": r.code_template,
            "description": r.description, "success_count": r.success_count,
            "total_saved_cost": r.total_saved_cost, "created_at": r.created_at,
        } for k, r in self._reflexes.items()}
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def learn(self, pattern_keywords: list[str], code_template: str,
              description: str = "", pattern_regex: str = ""):
        """学习新反射"""
        hash_id = hashlib.md5(code_template.encode()).hexdigest()[:8]
        reflex = Reflex(
            id=hash_id,
            trigger_keywords=pattern_keywords,
            trigger_regex=pattern_regex,
            code_template=code_template,
            description=description,
        )
        self._reflexes[hash_id] = reflex
        self._save()
        return hash_id

    def match(self, task: str) -> tuple[Reflex, dict] | tuple[None, None]:
        """
        匹配任务到最合适的反射
        
        Returns:
            (Reflex, variables) 或 (None, None)
        """
        task_lower = task.lower()
        candidates = []

        # Phase 1: 关键词匹配（候选集）
        for reflex in self._reflexes.values():
            score = sum(1 for kw in reflex.trigger_keywords if kw.lower() in task_lower)
            if score > 0:
                candidates.append((score, reflex))

        if not candidates:
            return None, None

        # 按匹配度排序
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_reflex = candidates[0]

        # Phase 2: 精确匹配（正则提取变量）
        variables = {}
        if best_reflex.trigger_regex:
            match = re.search(best_reflex.trigger_regex, task)
            if match:
                variables = match.groupdict()
            elif best_score < 2:
                return None, None  # 正则不匹配且关键词分低，拒绝

        # Phase 3: 填充模板
        code = best_reflex.code_template
        for key, value in variables.items():
            code = code.replace("{" + key + "}", str(value))

        # 如果模板还有未填充的占位符，需要 LLM
        if "{" in code and best_score < 3:
            return None, None

        return best_reflex, variables

    def execute(self, task: str, llm_cost_per_call: float = 0.003) -> dict:
        """
        执行条件反射（如果匹配到）
        
        Returns:
            {"reflex": True/False, "code": str, "saved_cost": float, ...}
        """
        reflex, variables = self.match(task)

        if not reflex:
            return {"reflex": False, "reason": "no_match"}

        # 填充变量
        code = reflex.code_template
        for key, value in variables.items():
            code = code.replace("{" + key + "}", str(value))

        # 如果还有未填充的占位符，提取文件名作为默认值
        file_match = re.search(r'([\w/]+\.\w+)', task)
        if file_match and "{path}" in code:
            code = code.replace("{path}", file_match.group(1))
        if "{files}" in code:
            code = code.replace("{files}", ".")

        # 执行
        try:
            import subprocess
            result = subprocess.run(code, shell=True, capture_output=True, text=True, timeout=30)

            saved = llm_cost_per_call
            reflex.success_count += 1
            reflex.total_saved_cost += saved
            self._save()

            return {
                "reflex": True,
                "reflex_id": reflex.id,
                "code": code,
                "output": result.stdout or result.stderr or "(无输出)",
                "saved_cost": saved,
                "total_saved": reflex.total_saved_cost,
                "success_count": reflex.success_count,
            }
        except Exception as e:
            return {"reflex": True, "code": code, "error": str(e), "saved_cost": 0}

    def stats(self) -> dict:
        """反射系统统计"""
        total = len(self._reflexes)
        total_saved = sum(r.total_saved_cost for r in self._reflexes.values())
        total_success = sum(r.success_count for r in self._reflexes.values())
        top = sorted(self._reflexes.values(), key=lambda r: r.success_count, reverse=True)[:5]

        return {
            "total_reflexes": total,
            "total_successes": total_success,
            "total_saved": f"¥{total_saved:.4f}",
            "top_reflexes": [{"desc": r.description or r.id, "hits": r.success_count} for r in top],
        }
