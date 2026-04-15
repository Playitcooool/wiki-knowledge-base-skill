---
title: AGENTS.md vs CLAUDE.md: Complete Guide
source_path: AGENTS.md vs CLAUDE.md Complete Guide.md
source_type: md
category: guides
tags:
  - ai-agents
  - claude-code
  - coding-assistants
  - project-configuration
  - developer-workflows
status: generated
last_synced: 2026-04-15
---

# AGENTS.md vs CLAUDE.md: Complete Guide

## Summary
This source explains the difference between two configuration files used by AI coding assistants. It presents `AGENTS.md` as a tool-agnostic standard for sharing project instructions across assistants such as Cursor, GitHub Copilot, Windsurf, and Claude Code, while presenting `CLAUDE.md` as Anthropic-specific configuration for Claude Code. The main recommendation is a bridge pattern: keep broadly reusable project guidance in `AGENTS.md`, then use `CLAUDE.md` to reference it and hold Claude-only extensions such as skills, sub-agents, and MCP-related settings.

## Content

### Core Positioning
- `AGENTS.md` is described as a portable instruction layer for multiple AI coding environments.
- `CLAUDE.md` is described as Claude Code’s native configuration surface with support for Claude-specific features.

### What the Source Says About `AGENTS.md`
- It is framed as an open standard for providing context to coding agents.
- The source argues that its main advantage is portability across tools and teams.
- It is compared to a README for AI assistants, but with agent-oriented operational guidance.

### What the Source Says About `CLAUDE.md`
- It supports hierarchical loading, including global and project-level configuration.
- It can reference skills, custom sub-agents, and MCP server configuration.
- It is useful when a team wants Claude-specific behavior beyond shared project instructions.

### Key Differences Highlighted by the Source
| Dimension | `AGENTS.md` | `CLAUDE.md` |
| --- | --- | --- |
| Scope | Cross-tool | Claude Code specific |
| Portability | High | Low |
| Skills support | No | Yes |
| Sub-agent support | No | Yes |
| Global config | No | Yes |
| MCP integration | No | Yes |

### Recommended Bridge Pattern
- Put the core project instructions in `AGENTS.md`.
- Use `CLAUDE.md` as a thin wrapper that points Claude to `AGENTS.md`.
- Keep Claude-only details in `CLAUDE.md`, such as skill names and custom agent references.

### Guidance on What to Include
- Project overview
- Tech stack
- Build, test, and lint commands
- High-level architecture notes

### Guidance on What Not to Include
- Obvious conventions the model can infer
- Details already discoverable from project files
- Exhaustive file-by-file documentation
- Generic advice with low operational value

### Advanced Topic: Skills
- The source presents Claude skills as reusable folders centered on `SKILL.md`.
- Skills are framed as a way to package repeatable task knowledge for agent invocation.

### Main Takeaway
The source recommends a layered setup: use `AGENTS.md` as the stable shared standard, and use `CLAUDE.md` only where Claude-specific functionality adds value.

## Key Entities
- `AGENTS.md`
- `CLAUDE.md`
- Claude Code
- Cursor
- GitHub Copilot
- Windsurf
- Zed
- MCP
- Agent Skills

## Related Files Index
- [[pages/guides/chatgpt-vs-claude-2026-comparison]] - Both documents compare major AI assistant ecosystems and discuss where Claude-specific workflows differ from broader tool usage.
- [[pages/research/automated-alignment-researchers]] - Both documents discuss agentic AI workflows, with this file focused on configuration and the research note focused on autonomous experimentation.
