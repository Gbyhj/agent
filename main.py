#!/usr/bin/env python3
"""
Agent CLI v5 — 智能路由 + 搜索 + 导出 + 模板

用法:
    python -m agent.main                          # 交互模式
    python -m agent.main "分析项目架构"            # 单任务
    python -m agent.main --template code-review    # 使用模板
    python -m agent.main --test                    # 测试
"""
from __future__ import annotations

import os, sys, asyncio, argparse, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.agent import Agent, AgentConfig
from agent.tools.builtin import (
    ReadFileTool, WriteFileTool, ListDirTool, GrepTool, BashTool, WebFetchTool,
)
from agent.tools.web_search import WebSearchTool
from agent.tools.templates import TaskTemplates
from agent.tools.export import ConversationExporter
from agent.providers.router import SmartRouter
from agent.memory.memory import MemorySystem


def parse_args():
    p = argparse.ArgumentParser(description="Agent v5 — 智能路由 + 搜索 + 导出")
    p.add_argument("task", nargs="?", help="任务描述")
    p.add_argument("--provider", default="", help="LLM Provider（空=智能路由）")
    p.add_argument("--model", default="", help="模型（空=智能路由）")
    p.add_argument("--api-key", default=os.environ.get("AGENT_API_KEY", os.environ.get("OPENAI_API_KEY", "")), help="API Key")
    p.add_argument("--max-turns", type=int, default=20, help="最大轮次")
    p.add_argument("--plan", action="store_true", help="Plan 模式")
    p.add_argument("--auto", action="store_true", help="Auto 模式")
    p.add_argument("--test", action="store_true", help="运行测试")
    p.add_argument("--template", "-t", help=f"任务模板: {', '.join(TaskTemplates.TEMPLATES.keys())}")
    p.add_argument("--target", default=".", help="模板目标路径")
    return p.parse_args()


async def main():
    args = parse_args()

    if args.test:
        from agent.test_agent import main as run_tests
        await run_tests()
        return

    # 模板模式
    if args.template:
        tmpl = TaskTemplates()
        task = tmpl.get(args.template, target=args.target, files=args.target, project="Agent")
        if not task:
            print(f"未知模板: {args.template}")
            print(f"可用: {', '.join(tmpl.TEMPLATES.keys())}")
            return
        print(f"📋 模板: {tmpl.TEMPLATES[args.template]['name']}")
    else:
        task = args.task

    # 智能路由 或 手动指定
    if not args.provider:
        router = SmartRouter()
        llm = router.route(task or "")
        provider, model = llm.provider, llm.model
        api_key = llm.api_key
    else:
        provider, model = args.provider, args.model
        api_key = args.api_key

    config = AgentConfig(provider=provider, model=model, api_key=api_key, max_turns=args.max_turns)
    if args.plan: config.mode = "plan"
    elif args.auto: config.mode = "auto"

    agent = Agent(config)
    agent.register_tools([
        ReadFileTool(), WriteFileTool(), ListDirTool(),
        GrepTool(), BashTool(), WebFetchTool(), WebSearchTool(),
    ])
    exporter = ConversationExporter()

    # 交互模式
    if not task:
        from agent.core.shell import PlanActShell
        shell = PlanActShell(agent)
        await shell.run()
        return

    # 单任务模式
    print(f"\n{'='*60}")
    print(f"  Agent v5 — {provider}/{model}")
    print(f"  模式: {config.mode} · 工具: {len(agent.registry)}")
    print(f"{'='*60}")

    t0 = time.time()
    result = await agent.run(task)
    elapsed = time.time() - t0

    print(f"\n{'='*60}")
    print(f"  完成 · {result.turns} 轮 · {len(result.tool_calls)} 工具调用 · {elapsed:.1f}s")
    print(f"{'='*60}\n{result.final_answer}\n{'='*60}")

    # 自动导出
    export_path = exporter.export_markdown(
        result.session_id, task, [], result.tool_calls, result.final_answer
    )
    print(f"\n📝 对话已导出: {export_path}")


if __name__ == "__main__":
    asyncio.run(main())
