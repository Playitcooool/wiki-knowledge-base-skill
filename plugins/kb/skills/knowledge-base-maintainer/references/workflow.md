# Workflow Reference

## Dry-Run First
Use `/kb:ingest` in preview mode to inspect changes without writing files.

Implementation detail:

```bash
python3 scripts/kb-ingest.py --root .
```

Expected output fields:
- `added sources`
- `updated sources`
- `deleted sources`
- `processed pages`
- `conflicts`

## Apply Mode
When conflicts are acceptable, use `/kb:ingest` with explicit write intent.

Implementation detail:

```bash
python3 scripts/kb-ingest.py --root . --apply
```

Apply mode updates:
- `pages/*`
- `pages/index.md`
- `log.md`

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
  - Action: do not auto-delete old page; confirm with user.
- Manual page protection:
  - Trigger: mapped page has `status` not equal to `generated`.
  - Action: skip overwrite and report conflict.
- Conversion failure:
  - Trigger: converter unavailable or extraction failed.
  - Action: report conflict and keep source unprocessed.

## Conversion Dependency Policy
- Preferred converter: bundled `scripts/convert_source.py`.
- For PDF chain, converter policy should be:
  - Docling default
  - MinerU fallback
  - pypdf final fallback
- Use `python3 scripts/doctor.py` to inspect tool availability.
