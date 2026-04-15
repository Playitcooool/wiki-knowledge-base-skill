# Knowledge Base Maintainer

Tools and a Codex skill for building and incrementally maintaining an Obsidian-friendly knowledge base from source files.

## What This Repository Includes
- `scripts/convert_source.py`
  Convert `md`, `txt`, `html`, `docx`, and `pdf` sources into Markdown.
- `scripts/doctor.py`
  Check local conversion-tool availability.
- `skills/knowledge-base-maintainer/`
  A publishable Codex skill for ingesting `raw/` sources, updating `pages/`, rebuilding `pages/index.md`, and appending `log.md`.
- `raw/`, `pages/`, `pages/index.md`, `log.md`
  An example knowledge-base workspace.

## Repository Layout
```text
.
├── raw/                                   # Original source files
├── pages/                                 # Generated markdown knowledge pages
├── scripts/
│   ├── convert_source.py                  # Source -> markdown conversion
│   └── doctor.py                          # Tool availability checks
├── skills/
│   └── knowledge-base-maintainer/         # Publishable Codex skill
├── pages/index.md                         # Global knowledge-base entry page
└── log.md                                 # Local update log (not committed)
```

## Quick Start
Check local tool availability:

```bash
python3 scripts/doctor.py
```

Convert a single source file:

```bash
python3 scripts/convert_source.py raw/example.docx -o /tmp/example.md
python3 scripts/convert_source.py raw/example.pdf -o /tmp/example.md
```

Run a dry-run knowledge-base sync:

```bash
python3 skills/knowledge-base-maintainer/scripts/sync_kb.py --root .
```

Apply the sync:

```bash
python3 skills/knowledge-base-maintainer/scripts/sync_kb.py --root . --apply
```

## PDF Conversion Policy
PDF conversion is attempted in this order:
1. `Docling`
2. `MinerU`
3. `pypdf` fallback

`docling` and `mineru` are optional local backends. If neither is installed, the repository still works with the `pypdf` fallback.

## Installing The Skill
Clone the repository, then install or copy `skills/knowledge-base-maintainer` into your Codex skills directory.

If you use the built-in skill installer, point it at this repository path after publishing.

## Validation
Representative checks:

```bash
python3 -m py_compile scripts/convert_source.py scripts/doctor.py
python3 -m py_compile skills/knowledge-base-maintainer/scripts/sync_kb.py
python3 skills/knowledge-base-maintainer/scripts/sync_kb.py --root .
```

## Release Notes
- The repository does not yet declare an open-source license.
- If `raw/` contains third-party source material, review redistribution rights before making the repository public.

## Tracking Policy
- `raw/` is local source material and is ignored by git.
- `pages/` (including `pages/index.md`) is local generated knowledge output and is ignored by git.
- `log.md` is local runtime history and is ignored by git.
