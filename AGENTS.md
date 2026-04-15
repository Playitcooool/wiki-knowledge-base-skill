# AI Knowledge Base Operating Guide

This file defines the operating rules for any LLM/agent working in this knowledge base. The goal is to turn raw source materials into an indexed, traceable, and Obsidian-friendly knowledge network.

## 1. Directory Structure

Maintain the following three-layer structure in the current directory:

1. `raw/`
   - Stores the original source files only.
   - Allowed inputs include `pdf`, `docx`, `md`, `txt`, `html`, and other formats that can be converted into text.
   - Do not modify raw files unless the user explicitly asks for it.

2. `pages/`
   - Stores Markdown knowledge pages generated from `raw/`.
   - Organize files by topic using the path format: `pages/<category>/<slug>.md`
   - `<category>` must be one of `research`, `guides`, or `notes`.
   - If classification is unclear, use `notes` and mark the classification as `to be confirmed` in the generated content or update log.

3. `index.md`
   - This is the global index page, similar to a wiki homepage.
   - It should summarize categories, major topics, important relationships, and entry links.

4. `log.md`
   - This is the update log for the knowledge base.
   - It stores recently added, updated, deleted, or conflict-related records.

If any of these paths do not exist, create the missing structure first, then continue with the update.

## 2. Classification Rules

Each source file must be assigned one primary category. Use these concise categories by default:

- `research`: papers, reports, technical investigations, experiment writeups
- `guides`: comparisons, explainers, tool documentation, workflow guides
- `notes`: reading notes, informal notes, meeting notes

Classification principles:

- A file must have exactly one primary category, but it may have multiple tags.
- Classify by subject matter, not by file format.
- If a file fits multiple categories, choose the most central one and represent the others through related-file links.
- If classification is unclear, place the file under `notes` and explicitly mark that classification as pending confirmation.
- If the new classification conflicts with an existing classification, ask the user before moving it.

## 3. Single-File Conversion Rules

Every source file in `raw/` should have one corresponding Markdown file in `pages/`.

### 3.1 Tool-Assisted Extraction Stage

If a source file in `raw/` is not already Markdown, the agent must first run a tool-assisted extraction step before generating the final page.

Project-local tools:

- `python3 scripts/doctor.py`: check whether the local conversion toolchain is available
- `python3 scripts/convert_source.py <input>`: convert a raw source file to Markdown and print to stdout
- `python3 scripts/convert_source.py <input> -o <output>`: convert a raw source file to a Markdown file

Project defaults:

- DOCX -> Markdown: `pandoc`
- PDF -> Markdown: `pypdf` text extraction through `scripts/convert_source.py`
- scanned PDF OCR: not configured yet and must be reported as a dependency gap when needed

Extraction rules:

- Treat this as a preprocessing step, not as a separate knowledge layer.
- The source of truth remains the original file in `raw/`, not the temporary extraction output.
- Prefer local tools first.
- Use the simplest reliable tool for the file type instead of forcing one tool for every format.

Preferred tool strategy:

- `md` or `txt`: reuse directly with minimal normalization
- `html`: convert to Markdown with an HTML-to-Markdown converter
- `docx`: prefer `pandoc`, using `scripts/convert_source.py` as the project wrapper
- `pdf`: prefer PDF text extraction through `scripts/convert_source.py`; if the PDF is image-based, use OCR
- scanned documents or images: use OCR before summarization or indexing

Fallback behavior:

- If the first tool produces low-quality output, try one fallback tool or method before giving up.
- If no suitable local tool is available, report that dependency gap to the user before attempting installation or any network-dependent step.
- If extraction is partial, continue only if the remaining text is sufficient for a faithful summary and mark the page as partially extracted.
- If extraction quality is too poor to support a reliable page, do not invent missing content; log the failure and ask the user how to proceed.
- If project-local scripts exist for the file type, prefer them over ad hoc one-off commands so the workflow stays reproducible.

Handling temporary outputs:

- Do not treat temporary converted files as permanent knowledge-base content.
- Do not add temporary extraction outputs to `index.md`.
- If a tool writes intermediate files, keep them outside the main wiki structure or clean them up after use.

The target file must follow this structure:

```md
---
title: <document title>
source_path: <path relative to raw/>
source_type: <pdf|docx|md|...>
category: <primary category>
tags:
  - <tag 1>
  - <tag 2>
status: generated
last_synced: <YYYY-MM-DD>
---

# <document title>

## Summary
Provide a faithful summary of the source. Do not invent facts not present in the original file.

## Content
Convert or normalize the source into Markdown. Preserve the original structure where possible and reorganize by headings only when needed.

## Key Entities
- Core concepts, people, organizations, tools, datasets, etc.

## Related Files Index
- [[pages/<category>/<other-slug>]] - short reason for the relationship
```

Conversion requirements:

- For non-Markdown inputs, perform tool-assisted extraction before writing the final page.
- Preserve the core structure, headings, lists, and table meaning from the source.
- For PDF, Word, and similar formats, extract readable text first. If extraction is incomplete or unreliable, state that explicitly.
- Do not fabricate citations, authors, dates, experiment results, or conclusions.
- If the source is already good Markdown, keep the main body and only add the required frontmatter and index sections.
- If external tools were required, the generated page should reflect the original file faithfully rather than mirroring tool artifacts blindly.
- Use stable slugs. Prefer generating the slug from the title. If there is a collision, append a short disambiguation suffix.

## 4. Related Files Index Rules

Every `pages/*.md` file must end with a `## Related Files Index` section.

Prioritize these relationship types:

- same topic or problem area
- one file explains concepts used in another file
- one file cites, extends, compares with, or critiques another file
- same project, same author, or same toolchain
- relationship between an original paper, its notes, and its interpretation

Relationship rules:

- Link only to Markdown files in the `pages/` layer. Do not place `raw/` files directly in the index.
- Every relationship entry must include a short reason, not just a link.
- Prefer the most relevant 3 to 8 files instead of creating meaningless full mesh links.
- If there is not enough evidence that two files are related, do not force the relationship.

## 5. Global `index.md` Rules

`index.md` is the global wiki entry point and must be maintained continuously.

Recommended structure:

```md
# Knowledge Base Index

## Document Catalog

| Title | Category | Source File | Page | Last Synced |
| --- | --- | --- | --- | --- |
| Example Title | guides | `raw/example.md` | [[pages/guides/example]] | 2026-04-15 |

## Key Topics
- Topic name: [[pages/...]], [[pages/...]]

## Important Relations
- [[pages/...]] <-> [[pages/...]]: relationship note

```

Maintenance requirements:

- Every file in `pages/` must be reachable from `index.md`.
- Use a table in `## Document Catalog` to present the main index more clearly.
- The catalog table should include at least: `Title`, `Category`, `Source File`, `Page`, and `Last Synced`.
- Use lists, not tables, for `## Key Topics` and `## Important Relations`, because relationship navigation is easier to read in list form.
- Add topic-level aggregation entries for recurring themes so `index.md` does not become a plain file dump.
- When files are added, deleted, moved, or renamed, update `index.md` accordingly.
- Store update history in `log.md`, not in `index.md`.

## 6. How to Handle Update Commands

When the user issues a command such as “update the knowledge base”, “sync the index”, or “refresh the docs”, follow this workflow:

1. Scan `raw/` and `pages/`.
2. Detect three kinds of changes:
   - Added: a source file exists in `raw/` but no corresponding Markdown exists in `pages/`
   - Updated: the source content or title changed and the generated Markdown or indexes must be refreshed
   - Deleted: a `pages/` file references a `source_path` that no longer exists in `raw/`
3. Process them in this order:
   - Added: extract text if needed, then create the new `pages/<category>/<slug>.md`
   - Updated: re-run extraction if needed, then refresh the Markdown content, frontmatter, related-file index, `index.md`, and `log.md`
   - Deleted: remove the entry from `index.md`, record the change in `log.md`, and delete or archive the corresponding `pages/` file
4. Re-check all relationship links at the end to ensure they remain valid.

Update behavior requirements:

- Prefer incremental updates. Do not rebuild the entire knowledge base without a clear reason.
- If a file contains human-authored additions, do not overwrite them unless the user explicitly allows it. Only refresh the generated sections.
- If the update depends on external conversion tools, prefer the same tool chain previously used for that file when possible so results stay stable across sync runs.
- Prefer project-local wrappers in `scripts/` over direct tool invocation when both are available.
- If it is unclear whether a file should be deleted, ask the user first.

## 7. Conflict Handling Rules

Do not make silent decisions in the following cases. Prompt the user instead:

- two different source files map to the same `slug`
- an old file may have been renamed rather than deleted and replaced
- one file could reasonably belong to multiple primary categories, and the choice would materially affect retrieval
- newly extracted content conflicts with the previous summary or relationship index
- source extraction fails or is severely incomplete
- required external tooling is missing, inconsistent, or produces materially different results than the previous extraction
- a `pages/` file contains obvious manual edits that would be overwritten by auto-update

When reporting a conflict, always provide:

- the conflicting file paths
- the conflict type
- the recommended resolution
- what will happen if automatic processing continues

## 8. Obsidian Compatibility Rules

To support Obsidian graph visualization and navigation:

- Prefer wiki links for internal references: `[[pages/category/file]]`
- Keep titles and slugs stable to avoid unnecessary link churn
- Reuse existing pages for the same topic instead of creating semantically duplicate pages
- Ensure that `index.md`, category groupings, and document pages form a traversable link network

## 9. Output Style Requirements

When the agent performs knowledge-base work, the result must be auditable and easy to review:

- clearly state which files were added, updated, or deleted
- clearly state which relationships were created and why
- clearly state whether any conflicts, missing data, or extraction failures were found
- use `to be confirmed` markers for uncertain conclusions instead of presenting them as facts
- append a concise dated record to `log.md` for every meaningful update run

## 10. Default Execution Principles

Unless the user says otherwise, always follow these defaults:

- convert faithfully first, build indexes second, update the global entry page last
- prefer stable naming before perfect categorization
- surface conflicts before making destructive changes
- preserve human-authored content before refreshing generated content

If this file conflicts with an explicit user instruction in the current session, follow the user’s instruction. Otherwise, follow this guide strictly.
