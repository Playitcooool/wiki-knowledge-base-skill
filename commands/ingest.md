---
description: Build or update the current folder as a knowledge base with one command.
---

# /kb:ingest

Build or update the current working directory as a knowledge base using the bundled `knowledge-base-maintainer` skill.

## Preflight

1. Treat the current working directory as the knowledge-base root unless the user explicitly gives another path.
2. Inspect whether `raw/` exists to detect a greenfield environment.
3. Preserve any user-authored pages whose frontmatter `status` is not `generated`.
4. If rename-like, classification, or extraction conflicts appear, surface them before destructive changes.

## Plan

1. Use `$knowledge-base-maintainer`.
2. Decide mode from user intent:
   - If the user asks to inspect, preview, review, or has not clearly asked to write, run ingest in preview mode.
   - If the user asks to build, bootstrap, update, sync, ingest, or refresh the knowledge base, run apply mode.
   - If the user asks whether the toolchain is ready, or conversion readiness is the blocker, run doctor first and then decide whether ingest can continue.
3. In a greenfield folder:
   - If mode is preview, explain that the folder is not initialized yet and no files were written.
   - If mode is apply, initialize `raw/`, `pages/`, `pages/index.md`, and `log.md`, then continue.

## Commands

Use the bundled skill and choose the matching local command:

```bash
python3 scripts/doctor.py
python3 scripts/kb-ingest.py --root .
python3 scripts/kb-ingest.py --root . --apply
```

Selection rules:

- Use `python3 scripts/doctor.py` when dependency readiness is the main question.
- Use `python3 scripts/kb-ingest.py --root .` for read-only preview.
- Use `python3 scripts/kb-ingest.py --root . --apply` when the user wants real changes.

If the user provided another target path, substitute that path for `.`.

## Verification

Confirm the outcome that matches the chosen path:

- doctor: tool availability and likely fallback chain were reported clearly
- preview: no files were modified
- apply: expected files under `pages/`, `pages/index.md`, and `log.md` were updated
- greenfield apply: required folders/files were bootstrapped
- any conflicts or partial extraction were reported explicitly

## Summary

Return a concise result block:

```md
## KB Ingest
- **Root**: <path>
- **Mode**: doctor | preview | apply
- **Status**: success | partial | failed
- **Added**: <count or n/a>
- **Updated**: <count or n/a>
- **Deleted**: <count or n/a>
- **Conflicts**: <count or n/a>
```

## Next Steps

- If the run was preview only, suggest re-running `/kb:ingest` with explicit write intent.
- If dependencies are missing, explain whether `pandoc`, Docling, MinerU, or `pypdf` is the blocker.
- If apply completed, suggest reviewing `pages/index.md`.
