# Workflow Reference

## Check First
Use `/kb:ingest` to always check what would change first before the LLM decides whether to apply.

Implementation detail:

```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .
```

Expected output fields:
- `added sources`
- `updated sources`
- `deleted sources`
- `processed pages`
- `conflicts`

If the check is clean, the LLM should auto-apply. If the check shows risk, the LLM should ask the user before continuing.
If the check shows a conversion capability gap, the LLM should keep `/kb:ingest` as the user-facing entrypoint and use the doctor output only to recommend the smallest required install step.

## Apply Mode
Apply is a backend write step. The LLM should only use it after a clean check or after the user confirms risky changes.

Implementation detail:

```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply
```

Apply mode updates:
- `pages/*`
- `pages/index.md`
- `log.md`

Delete operations are never silent. If apply would delete generated pages or asset directories, the LLM must ask for confirmation first.

## Greenfield Environment
If the directory has not been initialized yet (no `raw/`):
- `/kb:ingest` in preview mode prints a greenfield notice and exits without changes.
- `/kb:ingest` in apply mode bootstraps:
  - `raw/`
  - `pages/` + category folders
  - `pages/index.md`
  - `log.md`

After bootstrap, add source files to `raw/` and run `/kb:ingest` again with write intent.

## Conflict Types
- Possible rename:
  - Trigger: deleted source and added source share same normalized stem.
  - Action: if rename is unambiguous, migrate safely; otherwise ask the user before apply.
- Manual page protection:
  - Trigger: mapped page has `status` not equal to `generated`.
  - Action: skip overwrite, report conflict, and ask if the user wants to proceed with other safe changes.
- Conversion failure:
  - Trigger: converter unavailable or extraction failed.
  - Action: report conflict, keep source unprocessed, and ask only if user input is needed to continue.

## Conversion Dependency Policy
- Preferred converter: bundled `scripts/convert_source.py`.
- Capability tiers:
  - Base support: `md` / `txt`
  - Default rich-document ingestion: `requirements-markitdown.txt`
  - Local `.docx` / `.html` fallback: `pandoc`
  - Enhanced OCR PDF support: `requirements-optional.txt`
- Rich-document routing policy:
  - `MarkItDown` first for supported rich-document formats
  - `pandoc` fallback for `.docx` / `.html` when `MarkItDown` fails after it is installed
  - OCR fallback chain for thin scanned PDFs
- For PDF chain, converter policy should be:
  - Docling default
  - MinerU fallback
  - pypdf final fallback
- Use `python3 skills/knowledge-base-maintainer/scripts/doctor.py` to inspect tool availability.
