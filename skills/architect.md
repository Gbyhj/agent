# Architecture Analysis Skill

## When to use
User asks to analyze, evaluate, or review project architecture.

## Process
1. Map module dependencies (read __init__.py, imports)
2. Identify design patterns (factory, strategy, observer, etc.)
3. Check layering: No upward dependencies · Clean separation
4. Score: cohesion · coupling · complexity

## Output format
```
## Architecture Map
[module tree with dependency arrows]

## Patterns Identified
- Pattern name: where · why

## Layering Check
✅/⚠️/❌ per layer

## Score: X/10
```
