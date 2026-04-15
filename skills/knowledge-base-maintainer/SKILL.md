---
name: knowledge-base-maintainer
description: Build and maintain an Obsidian-style knowledge base from source files in raw/. Use when users ask to ingest/update documents with one command (`kb-ingest`), including first-time bootstrap in a greenfield directory, refresh of pages/index.md and log.md, detection of added/updated/deleted sources, and conflict-aware dry-run audits.
---

# Knowledge Base Maintainer

## Overview
Maintain a three-layer knowledge base (`raw/`, `pages/`, `pages/index.md` + `log.md`) with incremental updates and auditable output. Prefer project-local conversion scripts when present.

## Workflow
1. Run ingest dry-run first:
```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .
```
2. Apply ingest changes:
```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply
```
3. If required conversion tooling is missing, run:
```bash
python3 scripts/doctor.py
```

## Greenfield Handling
- If `raw/` does not exist yet:
  - `kb-ingest` (dry-run) returns a greenfield notice and no changes.
  - `kb-ingest --apply` bootstraps `raw/`, `pages/`, `pages/index.md`, and `log.md`.
- After bootstrap, place source files in `raw/` and run `kb-ingest --apply` again.

## What The Script Does
- Ensures required structure exists (`raw/`, `pages/research`, `pages/guides`, `pages/notes`, `pages/index.md`, `log.md`) in apply mode.
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
- Rebuilds `pages/index.md` document catalog and relation summary.
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
- Use `scripts/kb-ingest.py` as the public entry point, with `scripts/sync_kb.py` as the shared engine.
