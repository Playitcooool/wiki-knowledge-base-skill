---
name: knowledge-base-maintainer
description: Build and maintain an Obsidian-style knowledge base from source files in raw/. Use when users ask to ingest or update documents through the single command `/kb:ingest`, including first-time bootstrap in a greenfield directory, refresh of pages/index.md and log.md, detection of added/updated/deleted sources, and conflict-aware previews.
---

# Knowledge Base Maintainer

## Overview
Maintain a three-layer knowledge base (`raw/`, `pages/`, `pages/index.md` + `log.md`) with incremental updates and auditable output, using bundled conversion scripts.

For ordinary users, `preview` and `apply` are backend execution modes. The LLM should always check what would change first, auto-apply when the check is clean, and ask before risky writes. Any delete operation must be confirmed before apply continues.

User-facing policy:
- Keep `/kb:ingest` as the only public entrypoint.
- Treat capability checks and dependency installs as follow-up guidance, not as the first thing the user has to learn.
- Prefer the lightest supported path first, and only surface extra installation steps when the input actually needs them.
- Treat `MarkItDown` as the default rich-document ingestion path for knowledge-base building, not as a high-fidelity layout-preservation tool.

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
3. If preview reports a conversion capability gap, run:
```bash
python3 skills/knowledge-base-maintainer/scripts/doctor.py
```
4. Tell the user only the install step needed for the current file type:
   - Base support: `md` / `txt`
   - Default rich-document ingestion: `requirements-markitdown.txt`
   - Local `.docx` / `.html` fallback: `pandoc`
   - Enhanced OCR PDF support: `requirements-optional.txt`

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
- Uses `MarkItDown` first for supported rich-document inputs, then falls back to the existing local conversion chain when `MarkItDown` returns weak output or format-specific recovery is needed.
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
- Phrase conversion failures in capability terms when possible, for example missing DOCX support or missing OCR PDF support, instead of exposing backend selection details by default.
- If `MarkItDown` is missing, treat that as a blocking capability gap for supported rich-document inputs and tell the user to install `requirements-markitdown.txt`.

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
