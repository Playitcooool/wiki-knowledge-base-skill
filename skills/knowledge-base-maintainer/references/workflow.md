# Workflow Reference

## Dry-Run First
Use `kb-ingest` dry-run (default) to inspect changes without writing files:

```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .
```

Expected output fields:
- `added sources`
- `updated sources`
- `deleted sources`
- `processed pages`
- `conflicts`

## Apply Mode
When conflicts are acceptable, apply incremental updates:

```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply
```

Apply mode updates:
- `pages/*`
- `pages/index.md`
- `log.md`

## Greenfield Environment
If the directory has not been initialized yet (no `raw/`):
- `kb-ingest --root .` prints a greenfield notice and exits without changes.
- `kb-ingest --root . --apply` bootstraps:
  - `raw/`
  - `pages/` + category folders
  - `pages/index.md`
  - `log.md`

After bootstrap, add source files to `raw/` and run `kb-ingest --apply` again.

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
- Preferred converter: repository-local `scripts/convert_source.py`.
- For PDF chain, converter policy should be:
  - Docling default
  - MinerU fallback
  - pypdf final fallback
- Use `python3 scripts/doctor.py` to inspect tool availability.
