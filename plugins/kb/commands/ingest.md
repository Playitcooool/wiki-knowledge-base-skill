---
description: Build or update the current folder as a knowledge base with one command.
---

# /kb:ingest

Build or update the current working directory as a knowledge base using the bundled `knowledge-base-maintainer` skill.

For normal users, `preview` and `apply` are backend execution modes. The LLM should always check what would change first, auto-apply when the check is clean, and ask the user before risky writes. Any delete operation must be confirmed before apply continues.

## Preflight

1. Treat the current working directory as the knowledge-base root unless the user explicitly gives another path.
2. Inspect whether `raw/` exists to detect a greenfield environment.
3. Preserve any user-authored pages whose frontmatter `status` is not `generated`.
4. If rename-like, classification, or extraction conflicts appear, surface them before destructive changes.

## Plan

1. Use `$knowledge-base-maintainer`.
2. Decide mode from user intent:
   - Always check what would change first by running ingest in dry-run mode.
   - If the check is clean and the user asked to build, bootstrap, update, sync, ingest, or refresh, auto-apply.
   - If the check shows risk, ask the user before apply continues.
   - If the user asks whether the toolchain is ready, or conversion readiness is the blocker, run doctor first and then decide whether ingest can continue.
3. In a greenfield folder:
   - If mode is dry-run, explain that the folder is not initialized yet and no files were written.
   - If the check is clean and the user asked to build, initialize `raw/`, `pages/`, `pages/index.md`, and `log.md`, then continue.
4. Risk policy:
   - If the check shows delete operations, list the generated pages/assets to delete and ask for confirmation.
   - If the check shows rename ambiguity, manual-page protection, slug conflicts, or conversion/dependency blockers, ask before apply.

## Commands

Use the bundled skill and choose the matching local command:

```bash
python3 skills/knowledge-base-maintainer/scripts/doctor.py
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply
```

Selection rules:

- Use `python3 skills/knowledge-base-maintainer/scripts/doctor.py` when dependency readiness is the main question.
- Use `python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .` to always check what would change first.
- Use `python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply` only after a clean check or after the user confirms risky changes such as delete operations.

If the user provided another target path, substitute that path for `.`.

## Verification

Confirm the outcome that matches the chosen path:

- doctor: tool availability and likely fallback chain were reported clearly
- dry-run: no files were modified and risky changes that require the LLM to ask are surfaced clearly
- apply: expected files under `pages/`, `pages/index.md`, and `log.md` were updated
- greenfield apply: required folders/files were bootstrapped
- any conflicts, delete operations, or partial extraction were reported explicitly

## Summary

Return a concise result block:

```md
## KB Ingest
- **Root**: <path>
- **Mode**: doctor | dry-run | apply
- **Status**: success | partial | failed
- **Added**: <count or n/a>
- **Updated**: <count or n/a>
- **Deleted**: <count or n/a>
- **Conflicts**: <count or n/a>
```

## Next Steps

- If the run was dry-run only, explain whether the LLM will auto-apply next or needs to ask for confirmation.
- If dependencies are missing, explain whether `pandoc`, Docling, MinerU, or `pypdf` is the blocker.
- If apply completed, suggest reviewing `pages/index.md`.
