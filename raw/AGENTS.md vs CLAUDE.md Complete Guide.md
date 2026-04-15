---
title: "AGENTS.md vs CLAUDE.md: Complete Guide"
source: "https://substratia.io/blog/agents-md-vs-claude-md/"
author:
  - "[[Substratia]]"
published: 2026-01-11
created: 2026-04-15
description: "Learn the differences between AGENTS.md and CLAUDE.md files, when to use each, and best practices for configuring AI coding agents like Claude Code, Cursor, and GitHub Copilot."
tags:
  - "clippings"
---
If you're using AI coding assistants like Claude Code, Cursor, or GitHub Copilot, you've probably encountered both AGENTS.md and CLAUDE.md files. But what's the difference, and when should you use each? This guide breaks down everything you need to know.

### Quick Summary

- **AGENTS.md** - Universal standard, works across multiple AI tools
- **CLAUDE.md** - Claude Code specific, optimized for Anthropic's agent
- **Best Practice** - Use CLAUDE.md to point to AGENTS.md for compatibility

## What is AGENTS.md?

AGENTS.md is an open standard for providing context to AI coding agents. Think of it as a README file specifically designed for AI assistants. It has first-class support in most popular AI IDEs and coding agents:

- **Cursor** - Full native support
- **Zed** - Built-in recognition
- **GitHub Copilot** - Workspace context
- **Windsurf** - Automatic loading
- **Claude Code** - Supported via CLAUDE.md reference

The benefit of AGENTS.md is portability. If you switch between AI tools or collaborate with team members using different assistants, AGENTS.md ensures everyone gets the same project context.

## What is CLAUDE.md?

CLAUDE.md is Claude Code's native configuration file. It's specifically designed for Anthropic's Claude and offers some unique features:

- **Hierarchical loading** - Global (~/.claude/CLAUDE.md) and project-level
- **Skills integration** - Direct access to Agent Skills
- **Sub-agent definition** - Create custom agents in.claude/agents/
- **MCP server configuration** - Model Context Protocol setup

## Key Differences

| Feature | AGENTS.md | CLAUDE.md |
| --- | --- | --- |
| Compatibility | Universal (Cursor, Copilot, etc.) | Claude Code only |
| Skills Support | No | Yes |
| Sub-agents | No | Yes |
| Global Config | No | Yes (~/.claude/CLAUDE.md) |
| MCP Integration | No | Yes |

## Best Practice: The Bridge Pattern

The recommended approach is to use both files together. Create your main instructions in AGENTS.md (for universal compatibility), then have CLAUDE.md reference it:

```
# CLAUDE.md

# Project Configuration
See AGENTS.md for detailed project instructions.

# Claude-Specific Extensions
## Skills Available
- /commit - Smart commit messages
- /review - Code review helper

## Sub-agents
See .claude/agents/ for custom agent definitions.
```

This pattern gives you the best of both worlds: universal compatibility via AGENTS.md, plus Claude-specific features via CLAUDE.md.

## What to Put in Your Configuration

### Essential Information

- **Project overview** - What the project does in 1-2 sentences
- **Tech stack** - Languages, frameworks, key dependencies
- **Build commands** - How to install, build, test, lint
- **Architecture notes** - High-level structure that isn't obvious from code

### What NOT to Include

- Obvious conventions the AI already knows
- Information easily discoverable from package.json or similar
- Detailed file-by-file descriptions (keep in separate docs)
- Generic advice like "write clean code"

### Pro Tip: Keep It Minimal

Research shows that shorter, more focused configuration files perform better than comprehensive documentation dumps. The AI can always read more files if needed - your config file should just point it in the right direction.

## Advanced: Agent Skills

If you're using Claude Code, you can extend its capabilities with Agent Skills. Skills are folders containing a SKILL.md file that teaches Claude how to perform specific tasks:

```
.claude/skills/
├── commit/
│   └── SKILL.md
├── deploy/
│   ├── SKILL.md
│   └── deploy.sh
└── test/
    └── SKILL.md
```

Skills are powerful because they package your expertise into reusable components that Claude can invoke when needed.

## Tips for Creating Great Configs

Creating these configuration files is straightforward once you understand the patterns. Check out our [Prompt Optimizer](https://substratia.io/tools/prompt-optimizer/) and [agent building guide](https://substratia.io/blog/how-to-build-claude-agents/) for best practices and templates.

- Start with negative prompts (what NOT to do)
- Add specific capabilities for your use case
- Include guardrails and safety rules
- Iterate based on real-world performance

## Conclusion

Both AGENTS.md and CLAUDE.md serve important purposes in AI agent configuration. Use AGENTS.md for universal compatibility across tools, and CLAUDE.md for Claude-specific features like Skills and sub-agents. The bridge pattern - having CLAUDE.md reference AGENTS.md - gives you the best of both worlds.

Remember: keep your configurations minimal and focused. The goal is to give the AI the context it needs to be productive, not to document every aspect of your project.

## Further Reading

- [How to Build Claude Agents: A Complete Guide](https://substratia.io/blog/how-to-build-claude-agents/)
- [Mastering Negative Prompts for AI Agents](https://substratia.io/blog/mastering-negative-prompts/)
- [Substratia Documentation](https://substratia.io/docs/)