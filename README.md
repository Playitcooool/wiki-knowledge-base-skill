# Knowledge Base Maintainer

Tools and a Codex skill for building and incrementally maintaining an Obsidian-friendly knowledge base from source files.

## What This Repository Includes
- `skills/knowledge-base-maintainer/`
  A publishable Codex skill for converting sources, checking tool availability, ingesting `raw/` sources, updating `pages/`, rebuilding `pages/index.md`, and appending `log.md`.
- `raw/`, `pages/`, `pages/index.md`, `log.md`
  An example knowledge-base workspace.

## Repository Layout
```text
.
├── raw/                                   # Original source files
├── pages/                                 # Generated markdown knowledge pages
├── skills/
│   └── knowledge-base-maintainer/         # Publishable Codex skill
│       └── scripts/                       # convert_source.py, doctor.py, kb-ingest.py, sync_kb.py
├── pages/index.md                         # Global knowledge-base entry page
└── log.md                                 # Local update log (not committed)
```

## Quick Start
Check local tool availability:

```bash
python3 skills/knowledge-base-maintainer/scripts/doctor.py
```

Convert a single source file:

```bash
python3 skills/knowledge-base-maintainer/scripts/convert_source.py raw/example.docx -o /tmp/example.md
python3 skills/knowledge-base-maintainer/scripts/convert_source.py raw/example.pdf -o /tmp/example.md
```

Run ingest dry-run (safe preview):

```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .
```

Apply ingest updates:

```bash
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root . --apply
```

Greenfield note:
- If `raw/` does not exist, dry-run prints an initialization hint.
- `--apply` bootstraps `raw/`, `pages/`, `pages/index.md`, and `log.md`.

## PDF Conversion Policy
PDF conversion is attempted in this order:
1. `Docling`
2. `MinerU`
3. `pypdf` fallback

`docling` and `mineru` are optional local backends. If neither is installed, the repository still works with the `pypdf` fallback.

## Installing The Skill
Clone the repository, then install or copy `skills/knowledge-base-maintainer` into your Codex skills directory.

If you use the built-in skill installer, point it at this repository path after publishing.

Install Python dependency for bundled converter:

```bash
python3 -m pip install -r skills/knowledge-base-maintainer/requirements.txt
```

## Validation
Representative checks:

```bash
python3 -m py_compile skills/knowledge-base-maintainer/scripts/convert_source.py skills/knowledge-base-maintainer/scripts/doctor.py
python3 -m py_compile skills/knowledge-base-maintainer/scripts/sync_kb.py
python3 -m py_compile skills/knowledge-base-maintainer/scripts/kb-ingest.py
python3 skills/knowledge-base-maintainer/scripts/kb-ingest.py --root .
```

## Release Notes
- The repository does not yet declare an open-source license.
- If `raw/` contains third-party source material, review redistribution rights before making the repository public.

## Tracking Policy
- `raw/` is local source material and is ignored by git.
- `pages/` (including `pages/index.md`) is local generated knowledge output and is ignored by git.
- `log.md` is local runtime history and is ignored by git.
