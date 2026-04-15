# Command Conventions

This repository exposes the single slash command `/kb:ingest` as the public command surface.

Every command file in `commands/` should include:

- YAML frontmatter with `description`
- `Preflight`
- `Plan`
- `Commands`
- `Verification`
- `Summary`
- `Next Steps`

Command files prefixed with `_` are documentation only and should not be treated as user-facing slash commands.
