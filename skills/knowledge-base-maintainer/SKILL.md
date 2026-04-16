---
name: knowledge-base-maintainer
description: Build and maintain an Obsidian-style knowledge base from source files in raw/. Use when users ask to ingest or update documents through the single command `/kb:ingest`, including first-time bootstrap in a greenfield directory, refresh of pages/index.md and log.md, detection of added/updated/deleted sources, and conflict-aware previews.
---

# Knowledge Base Maintainer

## Overview
Maintain a three-layer knowledge base (`raw/`, `pages/`, `pages/index.md` + `log.md`) with incremental updates and auditable output, using bundled conversion scripts.

For ordinary users, `preview` and `apply` are backend execution modes. The LLM should always check what would change first, auto-apply when the check is clean, and ask before risky writes. Any delete operation must be confirmed before apply continues.

## Workflow
Public entrypoint: `/kb:ingest`

Implementation detail:
- preview mode -> `python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .`
- apply mode -> `python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply`
- dependency check -> `python3 skills/knowledge-base-maintainer/scripts/doctor.py`

1. Always check what would change first:
```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .
```
2. Auto-apply only when the preview is clean:
```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply
```
3. If required conversion tooling is missing, run:
```bash
python3 skills/knowledge-base-maintainer/scripts/doctor.py
```

## Greenfield Handling
- If `raw/` does not exist yet:
  - `/kb:ingest` in preview mode returns a greenfield notice and no changes.
  - `/kb:ingest` in apply mode bootstraps `raw/`, `pages/`, `pages/index.md`, and `log.md`.
- After bootstrap, place source files in `raw/` and run `/kb:ingest` again with write intent.

## What The Script Does
- Ensures required structure exists (`raw/`, `pages/research`, `pages/guides`, `pages/notes`, `pages/index.md`, `log.md`) in apply mode.
- Detects incremental changes:
  - Added: source exists in `raw/` but no mapped page.
  - Updated: source mtime is newer than mapped page.
  - Deleted: mapped page references a missing source.
- Converts sources through bundled `skills/knowledge-base-maintainer/scripts/convert_source.py`.
- Generates/updates page frontmatter and required sections:
  - `Summary`
  - `Content`
  - `Key Entities`
  - `Related Files Index`
- Rebuilds `pages/index.md` document catalog and relation summary.
- Appends a dated entry to `log.md`.

## Safety Rules
- Always check first before deciding whether to apply.
- Auto-apply only when the check is clean and the user asked to build or update.
- Ask the user before risky writes, including any delete operation.
- Skip auto-update when page frontmatter `status` is not `generated`.
- Treat possible renames as conflicts unless they can be migrated safely, and ask when ambiguity remains.
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
- Use `/kb:ingest` as the public entry point, with `skills/knowledge-base-maintainer/scripts/kb-ingest.py` and `skills/knowledge-base-maintainer/scripts/sync_kb.py` as the repository implementation.
