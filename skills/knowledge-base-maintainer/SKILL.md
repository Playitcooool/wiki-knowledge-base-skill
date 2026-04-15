---
name: knowledge-base-maintainer
description: Build and maintain an Obsidian-style knowledge base from source files in raw/. Use when users ask to ingest documents, sync knowledge pages, refresh index.md/log.md, detect added/updated/deleted sources, reconcile relationships, or run dry-run audits for knowledge-base updates.
---

# Knowledge Base Maintainer

## Overview
Maintain a three-layer knowledge base (`raw/`, `pages/`, `index.md` + `log.md`) with incremental updates and auditable output. Prefer project-local conversion scripts when present.

## Workflow
1. Run a dry-run scan first:
```bash
python3 skills/knowledge-base-maintainer/scripts/sync_kb.py --root .
```
2. Review added/updated/deleted counts and conflicts.
3. Apply changes only after conflict review:
```bash
python3 skills/knowledge-base-maintainer/scripts/sync_kb.py --root . --apply
```
4. If required conversion tooling is missing, run:
```bash
python3 scripts/doctor.py
```

## What The Script Does
- Ensures required structure exists (`raw/`, `pages/research`, `pages/guides`, `pages/notes`, `index.md`, `log.md`) in apply mode.
- Detects incremental changes:
  - Added: source exists in `raw/` but no mapped page.
  - Updated: source mtime is newer than mapped page.
  - Deleted: mapped page references a missing source.
- Converts sources through project-local `scripts/convert_source.py` when available.
- Generates/updates page frontmatter and required sections:
  - `Summary`
  - `Content`
  - `Key Entities`
  - `Related Files Index`
- Rebuilds `index.md` document catalog and relation summary.
- Appends a dated entry to `log.md`.

## Safety Rules
- Keep dry-run as default.
- Skip auto-update when page frontmatter `status` is not `generated`.
- Treat possible renames as conflicts and skip destructive deletion.
- Report conversion failures as conflicts; do not fabricate missing content.

## Classification Rules
- Classify to exactly one primary category:
  - `research`
  - `guides`
  - `notes`
- If uncertain, use `notes` and mark classification as `to be confirmed`.
- Keep slugs stable when a mapped page already exists.

## References
- Read [workflow](references/workflow.md) for conflict triage and expected outputs.
- Use `scripts/sync_kb.py` for deterministic sync; avoid ad hoc one-off filesystem updates.
