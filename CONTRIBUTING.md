# Contributing to Agent

感谢你的贡献！以下是参与项目的方式。

## 行为准则

- 尊重所有贡献者
- 建设性的代码审查
- 先讨论再实现（大改动先提 Issue）

## 如何贡献

### 提 Bug
1. 搜索已有 Issue，避免重复
2. 描述复现步骤、期望行为、实际行为
3. 附上环境信息（Python 版本、OS）

### 提功能建议
1. 先看 [创新方案](INNOVATIONS.md) 是否已规划
2. 描述使用场景和预期效果

### 提交代码
1. Fork → 创建分支 → 修改 → 提交 PR
2. 遵循 [AGENTS.md](AGENTS.md) 中的编码规范
3. 确保所有测试通过：`python beta_test.py`
4. 新功能需包含测试

## 开发环境

```bash
git clone https://github.com/Gbyhj/agent.git
cd agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m agent.main --test
```

## 测试

```bash
python -m agent.main --test        # 冒烟测试
python beta_test.py                # 21 场景内测
python tests/benchmark.py          # 基准测试
python synthetic_user_test.py      # UI 合成用户测试 (需要 Playwright)
```

## Commit 规范

```
<type>(<scope>): <subject>

类型: feat / fix / refactor / docs / test / chore
范围: core / tools / memory / providers / mcp / sandbox
```

## Code Review

参考 [CODE_REVIEW.md](docs/CODE_REVIEW.md)

## 大改动

需先提交 [Design Doc](docs/DESIGN_DOC_TEMPLATE.md) 并获批准后再实现。

---

再次感谢！
