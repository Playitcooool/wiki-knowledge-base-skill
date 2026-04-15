# Workflow Reference

## Dry-Run First
Use dry-run to inspect changes without writing files:

```bash
python3 skills/knowledge-base-maintainer/scripts/sync_kb.py --root .
```

Expected output fields:
- `added sources`
- `updated sources`
- `deleted sources`
- `processed pages`
- `conflicts`

## Apply Mode
When conflicts are acceptable, apply updates:

```bash
python3 skills/knowledge-base-maintainer/scripts/sync_kb.py --root . --apply
```

Apply mode updates:
- `pages/*`
- `pages/index.md`
- `log.md`

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
