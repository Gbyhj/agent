# AGENTS.md — Agent Context Engineering

> 参考: Google Agent White Paper · Harness 占据 90% · Context 质量决定输出质量

## 项目身份

- **名称**: Agent v5
- **语言**: Python 3.11+
- **许可**: MIT
- **仓库**: https://github.com/Gbyhj/agent
- **文档站**: https://agent.保康.top

## 技术栈

- **后端**: Python + Flask
- **AI**: DeepSeek V4 / OpenAI / Anthropic / Ollama
- **记忆**: ChromaDB 向量 + Markdown 文件
- **测试**: pytest + benchmark
- **部署**: Docker + Gunicorn + Nginx

## 架构约定

1. **分层隔离**: core/ → tools/ → memory/ → providers/，上层可依赖下层，禁止反向依赖
2. **每模块一文件**: 不超过 300 行
3. **工具注册**: 统一通过 ToolRegistry，不在 agent.py 中硬编码
4. **日志用 logger**: 禁止 print()（除 CLI 交互）

## 编码规范

1. **类型标注**: 所有公共函数必须标注参数和返回值类型
2. **文档字符串**: 每个类/函数必须有 docstring（一句话说明 + 参数）
3. **命名**: snake_case 函数/变量，PascalCase 类
4. **行宽**: 120 字符

## 提交规范

```
<type>(<scope>): <subject>
类型: feat/fix/refactor/docs/test/chore
范围: core/tools/memory/providers/mcp/sandbox
```

## 测试约定

1. 每个模块对应一个 test 文件
2. 修改代码 → 更新测试
3. API 变更 → 更新 CHANGELOG.md
4. 破坏性变更 → 标记 BREAKING CHANGE

## 文档约定

1. 架构变更 → 更新 BLUEPRINT.md
2. 版本发布 → 更新 CHANGELOG.md
3. 新模块 → 更新 README.md 项目结构
4. 对外接口 → 更新 apps/API.md

## 安全约定

1. API Key 只存环境变量
2. 路径操作必须经沙箱 validate_path()
3. Bash 命令必须经危险模式过滤
4. 用户数据 user_id 隔离

## AI 提示词约定

1. 分析任务先做 Planning Step
2. 复杂任务用 DeepSeek Pro，简单任务用 Flash
3. 代码生成后自动触发对抗审查
4. 任务完成后自动提取记忆
