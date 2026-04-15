# Codex Install

This repository is packaged as a whole-repo Codex capability bundle.

## Recommended Setup

1. Clone the repository somewhere stable:

```bash
git clone https://github.com/Playitcooool/wiki-knowledge-base-skill.git ~/.codex/vendor_imports/wiki-knowledge-base-skill
```

2. Link the bundled `skills/` directory into Codex native skill discovery:

```bash
mkdir -p ~/.agents/skills/wiki-knowledge-base
ln -s ~/.codex/vendor_imports/wiki-knowledge-base-skill/skills ~/.agents/skills/wiki-knowledge-base/skills
```

3. Restart Codex.

## Slash Command

The repository root also contains a Codex plugin manifest at `.codex-plugin/plugin.json` and root `commands/`.

If your Codex build supports loading local plugin packages, use the repository root as the plugin directory to expose:

```text
/kb:ingest
```

## Dependencies

- Out of the box: `md`, `txt`
- Install `pandoc` for `html` and `docx`
- Install minimal Python deps for basic PDF fallback:

```bash
pip install -r skills/knowledge-base-maintainer/requirements.txt
```

- Install optional enhanced PDF/OCR deps:

```bash
pip install -r skills/knowledge-base-maintainer/requirements-optional.txt
```
