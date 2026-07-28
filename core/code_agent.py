"""
CodeAgent Mode — Smolagents 最强单点

Agent 不只返回 JSON tool_call，而是直接写 Python 代码。
单步可以调用多个工具 + 循环 + 条件判断 + 变量。

用法:
    agent = Agent(config, mode="code")
    agent.run("搜索三个关键词，比较结果")
    
    传统:  3 轮 JSON tool_call → 3 次 LLM
    Code:  1 轮 Python → 1 次 LLM (省 67%)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class CodeInterpreter:
    """
    安全 Python 代码解释器

    限制:
    - 只能调用已注册的工具函数
    - 禁止 import（除非白名单）
    - 禁止文件系统写入（除非沙箱允许）
    - 输出截断到 5000 字符
    """

    ALLOWED_IMPORTS = {"json", "math", "re", "datetime", "collections", "itertools", "typing"}

    def __init__(self, tools: dict[str, Any], sandbox=None):
        self.tools = tools
        self.sandbox = sandbox
        self.output: list[str] = []

    def execute(self, code: str) -> str:
        """执行代码并返回输出"""
        self.output = []

        # 构建执行环境
        env = {"print": self._capture_print, "__builtins__": self._safe_builtins()}
        env.update(self.tools)  # 注入工具函数

        try:
            exec(code, env)
            return "\n".join(self.output)[:5000] or "(无输出)"
        except Exception as e:
            return f"执行错误: {e}"

    def _capture_print(self, *args, **kwargs):
        self.output.append(" ".join(str(a) for a in args))

    def _safe_builtins(self):
        """安全的内建函数白名单"""
        return {
            "range": range, "len": len, "str": str, "int": int, "float": float,
            "list": list, "dict": dict, "set": set, "tuple": tuple,
            "bool": bool, "type": type, "isinstance": isinstance,
            "enumerate": enumerate, "zip": zip, "sorted": sorted,
            "min": min, "max": max, "sum": sum, "abs": abs,
            "any": any, "all": all, "map": map, "filter": filter,
            "True": True, "False": False, "None": None,
            "print": self._capture_print,
        }


@dataclass
class CodeAgentResult:
    """CodeAgent 执行结果"""
    code: str
    output: str
    is_final_answer: bool
    error: str = ""


def code_agent_step(task: str, tools: dict[str, Any], llm=None) -> CodeAgentResult:
    """
    CodeAgent 单步执行
    
    参考 Smolagents CodeAgent._step_stream():
    1. 生成代码 → parse_code_blobs → 提取代码块
    2. 创建 python_interpreter 工具调用
    3. 安全执行 → 收集输出
    4. 判断 is_final_answer
    """
    if not llm:
        return CodeAgentResult(code="", output="无 LLM 可用", is_final_answer=True)

    tools_desc = "\n".join(f"- {name}: {tool.__doc__ or 'no description'}" for name, tool in tools.items())

    prompt = f"""你是一个 Code Agent。你可以写 Python 代码来完成任务。

可用工具函数（已在环境中，直接调用）:
{tools_desc}

任务: {task}

要求:
1. 用 Python 代码完成任务
2. 可以使用上述工具函数（不需要 import）
3. 把结果赋值给 final_answer 变量
4. 需要用 print() 输出中间结果

在 <code> 和 </code> 之间输出你的 Python 代码:"""

    resp = llm.chat([{"role": "user", "content": prompt}])
    raw = resp.content or ""

    # 提取代码块
    code = extract_code(raw)
    if not code:
        code = raw  # 如果没有标记，尝试直接执行

    # 执行
    interpreter = CodeInterpreter(tools)
    output = interpreter.execute(code)

    # 判断是否是最终答案
    is_final = "final_answer" in code or "print(" in code

    return CodeAgentResult(code=code, output=output, is_final_answer=is_final)


def extract_code(text: str) -> str:
    """从响应中提取代码（参考 Smolagents parse_code_blobs）"""
    # 匹配 <code>...</code>
    match = re.search(r"<code>\s*(.*?)\s*</code>", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 匹配 ```python ... ```
    match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 匹配 ``` ... ```
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return ""
