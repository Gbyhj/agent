"""
Plan/Act 双模式交互 CLI

设计融合:
- Cline: Plan mode(只读探索+策略) → Act mode(执行编辑)
- Grok Build: /model /new /resume /rewind 斜杠命令
- OpenClaw: 交互式聊天界面

命令:
    /plan       切换到 Plan 模式（只读）
    /act        切换到 Act 模式（执行）
    /auto       切换到自动模式（跳过审批）
    /model <id> 切换模型
    /tools      列出可用工具
    /memory     查看记忆
    /help       帮助
    /quit       退出
"""
from __future__ import annotations

import os
import sys
import asyncio

try:
    import readline  # Unix
except ImportError:
    try:
        import pyreadline3 as readline  # Windows
    except ImportError:
        readline = None

from .agent import Agent, AgentConfig
from .subagent import SubAgentCoordinator
from ..providers.llm import LLM


class PlanActShell:
    """Plan/Act 双模式交互 Shell"""

    BANNER = """
╔══════════════════════════════════════════╗
║        Agent v2 — Plan/Act Shell         ║
║  /plan 只读探索 · /act 执行 · /auto 自动  ║
║  /help 帮助 · /quit 退出                  ║
╚══════════════════════════════════════════╝"""

    HELP = """
  /plan        Plan 模式: 只读探索、分析、出策略（不修改文件）
  /act         Act 模式:  执行文件编辑和命令（需确认）
  /auto        Auto 模式: 自动执行（跳过确认）
  /model <id>  切换模型
  /provider <p>切换 Provider (deepseek/openai/anthropic/openrouter/ollama/siliconflow/zhipu)
  /tools       列出可用工具
  /memory      查看记忆存储
  /task <n>    委派并行子任务 (n=并行数)
  /help        显示帮助
  /quit        退出
"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.mode = "act"
        self.coordinator = SubAgentCoordinator(parent_llm=agent.llm)
        self._running = True
        self._history = []

    async def run(self):
        print(self.BANNER)
        print(f"\n  Provider: {self.agent.config.provider}")
        print(f"  Model:    {self.agent.config.model}")
        print(f"  Mode:     {self.mode}")
        print(f"  Tools:    {len(self.agent.registry)} registered\n")

        while self._running:
            try:
                user_input = input(f"\n[{self.mode}]> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not user_input:
                continue

            # 命令处理
            if user_input.startswith("/"):
                self._handle_command(user_input)
                continue

            # 任务执行
            await self._execute_task(user_input)

    def _handle_command(self, cmd: str):
        parts = cmd.split()
        cmd_name = parts[0].lower()

        if cmd_name == "/quit" or cmd_name == "/exit":
            self._running = False
            print("Bye.")

        elif cmd_name == "/plan":
            self.mode = "plan"
            self.agent.config.mode = "plan"
            print("✓ 切换到 Plan 模式（只读探索，不修改文件）")

        elif cmd_name == "/act":
            self.mode = "act"
            self.agent.config.mode = "act"
            print("✓ 切换到 Act 模式（可编辑文件和执行命令）")

        elif cmd_name == "/auto":
            self.mode = "auto"
            self.agent.config.mode = "auto"
            print("✓ 切换到 Auto 模式（自动执行，跳过确认）")

        elif cmd_name == "/model" and len(parts) > 1:
            new_model = parts[1]
            self.agent.config.model = new_model
            self.agent.llm = LLM(provider=self.agent.config.provider, model=new_model)
            print(f"✓ 模型切换为: {new_model}")

        elif cmd_name == "/provider" and len(parts) > 1:
            new_provider = parts[1]
            self.agent.config.provider = new_provider
            self.agent.llm = LLM(provider=new_provider, model=self.agent.config.model)
            print(f"✓ Provider 切换为: {new_provider}")

        elif cmd_name == "/tools":
            print(f"\n已注册工具 ({len(self.agent.registry)}):")
            for name in self.agent.registry.list_names():
                tool = self.agent.registry.get(name)
                damage = "⚠️" if getattr(tool, "is_destructive", False) else "✓"
                print(f"  {damage} {name}: {tool.description[:60]}")

        elif cmd_name == "/memory":
            from ..memory.memory import MemorySystem
            mem = MemorySystem()
            print("\n--- SOUL.md ---")
            print(mem.read_soul()[:500])
            print("\n--- MEMORY.md ---")
            print(mem.read_memory()[:500])

        elif cmd_name == "/help":
            print(self.HELP)

        elif cmd_name == "/task" and len(parts) > 1:
            print("批量任务模式: 输入多个任务，每行一个，空行结束")
            tasks = []
            while True:
                t = input(f"  任务 {len(tasks)+1}: ").strip()
                if not t:
                    break
                tasks.append({"role": "worker", "task": t})
            if tasks:
                asyncio.create_task(self._run_parallel(tasks))

        else:
            print(f"未知命令: {cmd_name}. 输入 /help 查看帮助。")

    async def _execute_task(self, user_input: str):
        """执行用户任务"""
        self._history.append({"role": "user", "content": user_input})

        self.agent.config.mode = self.mode
        try:
            result = await self.agent.run(user_input)

            print(f"\n{'─'*50}")
            print(f"  {result.final_answer[:500]}")
            if len(result.final_answer) > 500:
                print(f"  ... (共 {len(result.final_answer)} 字符)")
            print(f"{'─'*50}")
            print(f"  轮次: {result.turns} · 工具调用: {len(result.tool_calls)}")

            from ..memory.memory import MemorySystem
            MemorySystem().log_daily(f"[{self.mode}] {user_input[:80]}\n→ {result.final_answer[:200]}")

        except Exception as e:
            print(f"\n执行出错: {e}")

    async def _run_parallel(self, tasks: list[dict]):
        """并行执行多个子任务"""
        print(f"\n启动 {len(tasks)} 个并行子代理...")
        results = await self.coordinator.delegate_parallel(tasks)
        print(f"\n并行任务完成 ({len(results)}):")
        for r in results:
            status = "✓" if not r.error else "✗"
            print(f"  {status} [{r.role}] {r.result[:80]}... ({r.turns}t, {r.elapsed:.1f}s)")
