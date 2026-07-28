"""
VariablePool — Dify 全局变量传递

参考 Dify 源码:
    variable_pool = VariablePool()
    add_variables_to_pool(variable_pool, default_system_variables())
    add_node_inputs_to_pool(variable_pool, node_id=id, inputs=user_inputs)

支持路径解析: "node_id.output.result"
"""
from __future__ import annotations

import re
from typing import Any


class VariablePool(dict):
    """全局变量池 — 所有节点共享"""

    def set_node_output(self, node_id: str, key: str, value: Any):
        """设置节点输出变量"""
        if node_id not in self:
            self[node_id] = {}
        self[node_id][key] = value
        # 同时存快捷引用
        self[f"{node_id}.{key}"] = value

    def get_node_output(self, node_id: str) -> dict:
        """获取节点所有输出"""
        return self.get(node_id, {})

    def resolve(self, path: str) -> Any:
        """
        按路径取值

        支持格式:
        - "node_id.output" → 取节点输出
        - "node_id.output.result" → 取节点输出中的result字段
        - "node_id.output.result.key" → 深层路径
        """
        parts = path.split(".")
        value = self

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def resolve_template(self, text: str) -> str:
        """解析模板变量 {node_id.output.key}"""
        def replacer(match):
            path = match.group(1)
            result = self.resolve(path)
            return str(result) if result is not None else match.group(0)

        return re.sub(r"\{([\w.]+)\}", replacer, text)

    def inject_system_vars(self):
        """注入系统变量 (Dify default_system_variables)"""
        from datetime import datetime
        self["sys.timestamp"] = datetime.now().isoformat()
        self["sys.user_agent"] = "Agent v5"

    def merge_outputs(self, outputs: dict, prefix: str = ""):
        """批量合并输出"""
        for key, value in outputs.items():
            full_key = f"{prefix}.{key}" if prefix else key
            self[full_key] = value
