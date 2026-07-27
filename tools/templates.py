"""
Task Templates — 常用任务模板

用法:
    templates = TaskTemplates()
    prompt = templates.get("code-review").format(files="agent/core/agent.py")
"""
from __future__ import annotations


class TaskTemplates:
    """预设任务模板库"""

    TEMPLATES = {
        "code-review": {
            "name": "代码审查",
            "icon": "🔍",
            "prompt": """审查以下文件的代码质量：

{files}

请关注：
1. Bug 和逻辑错误（严重）
2. 安全问题（严重）
3. 性能问题（警告）
4. 代码风格和改进建议（建议）

对每个问题给出具体的文件路径、行号和修复方案。""",
        },
        "project-analysis": {
            "name": "项目分析",
            "icon": "📊",
            "prompt": """分析 {project} 项目的整体架构：

1. 列出所有主要模块及其职责
2. 分析模块间的依赖关系
3. 识别架构模式和设计模式
4. 指出潜在的架构问题

使用 read_file 和 grep 工具探索代码。""",
        },
        "refactor": {
            "name": "重构建议",
            "icon": "🔧",
            "prompt": """对 {target} 提出重构建议：

1. 分析现有实现的优缺点
2. 提出 2-3 种重构方案
3. 比较各方案的利弊
4. 推荐最佳方案并给出实施步骤

先阅读代码，再给出建议。不要直接修改文件。""",
        },
        "write-docs": {
            "name": "生成文档",
            "icon": "📝",
            "prompt": """为 {target} 生成文档：

1. 概述（一段话说明用途）
2. 核心 API（列出主要函数/类及其签名）
3. 使用示例（2-3 个实际例子）
4. 注意事项

读取源码后，生成一份清晰的 Markdown 文档。""",
        },
        "write-tests": {
            "name": "写单元测试",
            "icon": "🧪",
            "prompt": """为 {target} 编写单元测试：

1. 覆盖主要功能路径
2. 包含边界条件测试
3. 包含错误处理测试
4. 使用项目中已有的测试框架

先阅读源码和现有测试，然后编写新的测试文件。""",
        },
        "explain-code": {
            "name": "解释代码",
            "icon": "💡",
            "prompt": """详细解释 {target} 的代码逻辑：

1. 整体功能概述
2. 逐段解释关键代码
3. 关键数据结构说明
4. 执行流程图

用通俗易懂的方式解释，适合代码审查或新人学习。""",
        },
        "find-bug": {
            "name": "找 Bug",
            "icon": "🐛",
            "prompt": """在 {target} 中查找潜在的 Bug：

1. 空指针/None 引用
2. 资源泄漏（文件未关闭、连接未释放）
3. 竞态条件
4. 边界条件处理错误
5. 异常处理不当

仔细审查每一行代码，对每个问题给出具体位置和修复建议。""",
        },
        "dependency-check": {
            "name": "依赖检查",
            "icon": "📦",
            "prompt": """检查 {project} 的依赖情况：

1. 列出所有直接和间接依赖
2. 检查是否有已知漏洞的版本
3. 建议可以移除的冗余依赖
4. 建议可以更新的过时依赖

读取 requirements.txt/pyproject.toml/package.json 等依赖文件。""",
        },
    }

    def list_templates(self) -> list[dict]:
        """列出所有模板"""
        return [
            {"id": tid, "name": t["name"], "icon": t["icon"]}
            for tid, t in self.TEMPLATES.items()
        ]

    def get(self, template_id: str, **kwargs) -> str | None:
        """获取模板并填充参数"""
        t = self.TEMPLATES.get(template_id)
        if not t:
            return None
        return t["prompt"].format(**kwargs)
