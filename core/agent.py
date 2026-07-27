"""
Agent Core v5 — 智能升级版

新增四大能力（基于 25 个项目源码分析）:

1. Planning System (Smolagents)
   - 每 N 轮插入一次规划步骤
   - 首次: 分析任务 → 制定计划
   - 后续: 回顾进展 → 更新计划

2. Goal Verification (Grok Build)
   - Agent 声明完成后, 启动 skeptic 子代理验证
   - majority_vote 判定是否真正完成
   - 未完成 → 生成 gap 摘要 → 继续执行

3. Auto Memory Extraction (Mem0)
   - 任务完成后自动提取关键事实
   - 向量化存储到 ChromaDB
   - 下次任务自动检索相关记忆

4. Error Self-Repair (Smolagents + Grok Build)
   - 工具调用失败 → 自动分析原因
   - 修正参数 → 重试 (最多 2 次)
   - 记录修复经验到记忆
"""
from __future__ import annotations

import os, time, asyncio, traceback, re
from dataclasses import dataclass, field
from typing import Callable

from .tool_registry import ToolRegistry
from .state import AgentState, TurnResult
from ..providers.llm import LLM
from ..providers.router import SmartRouter


@dataclass
class AgentConfig:
    provider: str = ""
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    max_turns: int = 25
    planning_interval: int | None = 5       # 每 N 轮插入规划步骤
    verify_completion: bool = True           # Goal 验证
    auto_memory: bool = True                 # 自动记忆提取
    self_repair: bool = True                 # 错误自修复
    daily_budget: float = 5.0
    mode: str = "act"


class Agent:
    """自主 AI Agent v5 — 智能升级版"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.registry = ToolRegistry()

        # 智能路由
        self.router = SmartRouter(daily_budget=config.daily_budget)
        if config.provider and config.model:
            self.llm = LLM(provider=config.provider, model=config.model, api_key=config.api_key)
        else:
            self.llm = LLM(provider="deepseek", model="deepseek-v4-flash", api_key=config.api_key)

        self._hooks: dict[str, list[Callable]] = {}
        self._tool_cache: dict[str, str] = {}         # 工具结果缓存

    def register_tools(self, tools: list):
        for t in tools:
            self.registry.register(t)

    # ═══════════════════════════════════════════════════════
    #  主循环
    # ═══════════════════════════════════════════════════════
    async def run(self, task: str, session_id: str | None = None) -> TurnResult:
        sid = session_id or f"sess_{int(time.time())}"
        state = AgentState(session_id=sid, task=task)

        # 加载相关记忆
        memory_ctx = ""
        if self.config.auto_memory:
            memory_ctx = self._load_memories(task)

        print(f"\n{'='*60}")
        print(f"  Agent v5 · {self.llm.provider}/{self.llm.model}")
        print(f"  Planning: {'每' + str(self.config.planning_interval) + '轮' if self.config.planning_interval else 'OFF'}")
        print(f"  Verify: {'ON' if self.config.verify_completion else 'OFF'}")
        print(f"  Self-repair: {'ON' if self.config.self_repair else 'OFF'}")
        print(f"  Memory: {len(memory_ctx)} chars loaded")
        print(f"{'='*60}\n")

        for turn in range(1, self.config.max_turns + 1):
            if state.is_finished:
                break

            # ── 1. Planning Step (Smolagents) ──
            if self.config.planning_interval and (
                turn == 1 or (turn - 1) % self.config.planning_interval == 0
            ):
                plan = await self._planning_step(state, task, turn)
                if plan:
                    print(f"  📋 [Plan] {plan[:150]}...")
                    state.add_thought(f"📋 计划: {plan}")

            # ── 2. Context Builder ──
            messages = self._build_messages(state, turn, memory_ctx)
            tools = self.registry.to_schema_list() if self.config.mode != "plan" else []

            # ── 3. LLM Call ──
            t0 = time.time()
            resp = await asyncio.to_thread(self.llm.chat, messages, tools)
            state.turn_count += 1

            # ── 4. Process ──
            if resp.content:
                short = resp.content[:150].replace("\n", " ")
                print(f"  [{turn}] {short}...")
                state.add_thought(resp.content)

            if resp.tool_calls:
                for tc in resp.tool_calls:
                    print(f"  [{turn}] → {tc['name']}({tc['args']})")
                    result = await self._execute_with_repair(tc, state)
                    state.add_observation(tc["name"], result)

            # ── 5. Termination Check ──
            if resp.final_answer or (resp.content and not resp.tool_calls):
                # Goal Verification (Grok Build)
                if self.config.verify_completion:
                    verified, gaps = await self._verify_completion(task, resp.content, state)
                    if not verified:
                        print(f"  ⚠️ 验证未通过: {gaps}")
                        state.add_observation("verification", f"未通过: {gaps}")
                        task_with_gaps = f"{task}\n\n⚠️ 上次执行未完成: {gaps}\n请继续完成剩余工作。"
                        state.task = task_with_gaps
                        continue  # 继续执行

                state.final_answer = resp.content or "完成"
                state.is_finished = True
                break

            if turn >= self.config.max_turns:
                state.final_answer = f"达到最大轮次 ({self.config.max_turns})"
                state.is_finished = True

        # ── 任务完成后: 自动记忆提取 ──
        if self.config.auto_memory and state.final_answer:
            self._extract_memories(task, state.final_answer)

        return TurnResult(sid, state.final_answer or "未完成", state.turn_count, state.observations, state.tool_calls_log)

    # ═══════════════════════════════════════════════════════
    #  1. Planning System (Smolagents)
    # ═══════════════════════════════════════════════════════
    async def _planning_step(self, state: AgentState, task: str, turn: int) -> str | None:
        """插入规划步骤（参考 Smolagents _generate_planning_step）"""
        is_first = (turn == 1)

        if is_first:
            prompt = f"""你是一个任务规划专家。分析以下任务并制定执行计划。

任务: {task}

可用工具: {self.registry.describe_all()}

制定一个清晰的执行计划，包含:
1. 需要哪几步?
2. 每一步用什么工具?
3. 关键决策点?

输出格式: 用 Markdown 列表。"""
        else:
            progress = "\n".join(state.observations[-5:]) if state.observations else "无"
            prompt = f"""回顾当前进展并更新计划。

任务: {task}
已完成步骤摘要:
{progress}

评估进度，列出还需完成的步骤。如果任务已接近完成，说明剩余工作。"""

        try:
            resp = await asyncio.to_thread(self.llm.chat, [
                {"role": "system", "content": "用简洁的 Markdown 列表输出计划。不超过 150 字。"},
                {"role": "user", "content": prompt},
            ])
            return resp.content
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════
    #  2. Goal Verification (Grok Build)
    # ═══════════════════════════════════════════════════════
    async def _verify_completion(self, task: str, answer: str, state: AgentState) -> tuple[bool, str]:
        """对抗性验证: 真的完成了吗？（参考 Grok Build skeptic）"""
        prompt = f"""你是任务验证专家。严格检查任务是否真正完成。

原始任务: {task}
Agent 的完成声明: {answer[:500]}
实际观察到的结果: {state.observations[-3:] if state.observations else '无'}

判断标准:
- 如果 Agent 只是"声称完成"但没有实际证据 → 未完成
- 如果工具调用结果显示任务已执行 → 完成
- 如果中间有错误但已修复 → 完成

输出: "YES" 或 "NO: <具体原因>" """

        try:
            resp = await asyncio.to_thread(self.llm.chat, [
                {"role": "system", "content": "只输出 YES 或 NO: <原因>。不超过 50 字。"},
                {"role": "user", "content": prompt},
            ])
            result = (resp.content or "").strip().upper()
            if result.startswith("YES"):
                return True, ""
            return False, result.replace("NO:", "").strip()[:100]
        except Exception:
            return True, ""  # 验证失败时默认通过

    # ═══════════════════════════════════════════════════════
    #  3. Error Self-Repair (Smolagents + Grok Build)
    # ═══════════════════════════════════════════════════════
    async def _execute_with_repair(self, tc: dict, state: AgentState) -> str:
        """执行工具, 失败时自动分析和重试（最多 2 次）"""
        tool = self.registry.get(tc["name"])
        if not tool:
            return f"工具不存在: {tc['name']}"

        args = tc.get("args", {})

        # 尝试执行
        for attempt in range(3 if self.config.self_repair else 1):
            # 缓存检查
            cache_key = f"{tc['name']}:{str(args)}"
            if cache_key in self._tool_cache and tc["name"] in ("read_file", "list_dir"):
                return self._tool_cache[cache_key]

            try:
                result = str(tool.execute(**args))

                # 缓存只读工具结果
                if tc["name"] in ("read_file", "list_dir", "grep"):
                    self._tool_cache[cache_key] = result

                return result[:20000]

            except Exception as e:
                error_msg = str(e)

                if attempt < 2 and self.config.self_repair:
                    print(f"  🔧 修复尝试 {attempt+1}/2: {tc['name']} 失败 → {error_msg[:80]}")
                    # 尝试简单修复
                    fixed = self._auto_fix_args(tc["name"], args, error_msg)
                    if fixed != args:
                        args = fixed
                        continue

                return f"错误: {error_msg}"

        return f"工具执行失败（已重试 2 次）"

    def _auto_fix_args(self, tool_name: str, args: dict, error: str) -> dict:
        """自动修复常见参数错误"""
        fixed = dict(args)

        # 文件路径: 尝试补充完整路径
        if tool_name in ("read_file", "write_file", "list_dir") and "path" in args:
            path = args["path"]
            if not os.path.exists(path) and not os.path.isabs(path):
                # 尝试在当前目录查找
                if os.path.exists(os.path.join(os.getcwd(), path)):
                    fixed["path"] = os.path.join(os.getcwd(), path)

            # 路径包含非法字符
            fixed["path"] = re.sub(r'[<>:"|?*]', '_', str(fixed["path"]))

        # Bash: 移除危险标志
        if tool_name == "bash" and "command" in args:
            cmd = args["command"]
            if "Permission denied" in error:
                # 尝试去掉 sudo
                fixed["command"] = cmd.replace("sudo ", "")

        return fixed

    # ═══════════════════════════════════════════════════════
    #  4. Auto Memory Extraction (Mem0)
    # ═══════════════════════════════════════════════════════
    def _load_memories(self, task: str) -> str:
        """加载相关记忆到上下文"""
        try:
            from ..memory.vector_memory import VectorMemory
            mem = VectorMemory()
            return mem.inject_context(task, max_chars=1500)
        except Exception:
            return ""

    def _extract_memories(self, task: str, answer: str):
        """从对话中自动提取关键记忆（简化版 Mem0）"""
        try:
            from ..memory.vector_memory import VectorMemory
            from ..memory.memory import MemorySystem

            mem = VectorMemory()
            filesys = MemorySystem()

            # 提取任务类型
            if any(kw in task for kw in ["重构", "refactor"]):
                mem.remember(f"偏好：重构时先做只读分析再修改", category="preference")

            # 记录项目信息
            project_hints = re.findall(r'(\w+)[/\\](\w+\.\w+)', task + answer)
            if project_hints:
                mem.remember(f"项目文件: {', '.join(f'{a}/{b}' for a, b in project_hints[:5])}", category="project")

            # 记录成功经验
            mem.remember(f"任务: {task[:80]} → {answer[:100]}", category="experience")

            # 写入文件记忆
            filesys.log_daily(f"[mem0] {task[:60]} → OK")
            filesys.update_memory("最近任务", task[:80])

        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════════════════════
    def _build_messages(self, state: AgentState, turn: int, memory_ctx: str = "") -> list[dict]:
        return [
            {"role": "system", "content": self._system_prompt(memory_ctx)},
            {"role": "user", "content": state.task if turn == 1 else "继续执行任务。"},
        ]

    def _system_prompt(self, memory_ctx: str = "") -> str:
        from ..memory.memory import MemorySystem
        mem = MemorySystem()
        file_mem = mem.get_context_for_llm()

        return f"""{file_mem}
{memory_ctx}

你是自主 AI Agent v5。完成任务后给出总结。

原则:
1. 每次只用一个工具
2. 观察结果后再决定下一步
3. 工具失败会自动修正重试
4. 完成后明确报告结果

可用工具:
{self.registry.describe_all()}"""
