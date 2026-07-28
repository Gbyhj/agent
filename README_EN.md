# Agent v6

> Autonomous AI Agent — 16 open-source projects fused into one

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](https://github.com/Gbyhj/agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)

## What is Agent?

Agent is an autonomous AI assistant that reviews code, analyzes architecture, searches for information, and designs databases. It integrates 12 production-ready techniques from 18 industry research papers.

## 12 Production Techniques

| Technique | Source | Module |
|-----------|--------|--------|
| Thin Harness | Garry Tan / Claude Code leak | `engine/harness.py` |
| Caveman Mode | Reddit 10K+ · 65% token reduction | `features/caveman.py` |
| Skills System | Claude Code patterns | `skills/*.md` |
| Work-Order Prompt | Claude Code Guides | `features/work_order.py` |
| Durable Execution | LangGraph 1.0 | `features/durable.py` |
| Shadow/Assist/Auto | Pento | `features/modes.py` |
| Tool 5 Elements | SensusSoft | `tools/production.py` |
| 4-Layer Guardrails | eCorpIT | `infra/guards.py` |
| Cost Router | Pento · 40-85% savings | `features/cost_router.py` |
| Async Memory Pipeline | CallSphere | `memory/async_memory.py` |
| Memory Forgetting | Zep · Mem0 | `memory/async_memory.py` |
| Code Graph | CodeGraphContext MCP | `tools/code_graph.py` |

## Quick Start

```bash
pip install agent-cli
# or
git clone https://github.com/Gbyhj/agent.git
cd agent && python -m agent.main --test
```

## Online Demo

https://agent.保康.top

## Architecture

```
src/
├── engine/     Agent loop + state
├── infra/      Sessions · events · guards · flags  
├── features/   Caveman · modes · durable · work-order
├── memory/     File · vector · graph · async
├── tools/      Registry · production · code-graph
└── providers/  LLM · router · semantic · checks
```

## Research

https://agent.保康.top/reference — 18 articles · 40+ techniques
