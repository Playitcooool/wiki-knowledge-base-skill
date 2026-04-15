# Command Conventions

This plugin exposes the single slash command `/kb:ingest` for the bundled `knowledge-base-maintainer` skill.

Every command file in `commands/` should include:

- YAML frontmatter with `description`
- `Preflight`
- `Plan`
- `Commands`
- `Verification`
- `Summary`
- `Next Steps`

Command files prefixed with `_` are documentation only and should not be treated as user-facing slash commands.
