#!/usr/bin/env python3
"""
Incrementally maintain an Obsidian-friendly knowledge base.

This script is intentionally conservative:
- Supports dry-run by default.
- Skips destructive actions when rename-like conflicts are detected.
- Skips overwriting pages that do not declare `status: generated`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


RAW_DIR = "raw"
PAGES_DIR = "pages"
INDEX_FILE = f"{PAGES_DIR}/index.md"
LOG_FILE = "log.md"
SUPPORTED_CATEGORIES = ("research", "guides", "notes")
SUPPORTED_RAW_TYPES = {
    ".md",
    ".markdown",
    ".txt",
    ".html",
    ".htm",
    ".docx",
    ".pdf",
}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "that",
    "this",
    "using",
    "use",
    "guide",
    "notes",
    "note",
    "report",
    "paper",
    "study",
}


@dataclass
class PageRecord:
    path_abs: Path
    path_rel: str
    category: str
    source_path: str
    source_type: str
    title: str
    status: str
    last_synced: str
    tags: list[str]
    body: str
    frontmatter: dict[str, str | list[str]]

    @property
    def wiki_link(self) -> str:
        return f"[[{self.path_rel[:-3]}]]"


def split_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    if not text.startswith("---\n"):
        return {}, text
    marker = "\n---\n"
    end = text.find(marker, 4)
    if end < 0:
        return {}, text

    fm_text = text[4:end]
    body = text[end + len(marker) :]

    frontmatter: dict[str, str | list[str]] = {}
    current_key: str | None = None
    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            value = line[4:].strip()
            existing = frontmatter.get(current_key)
            if not isinstance(existing, list):
                existing = []
                frontmatter[current_key] = existing
            existing.append(value)
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            current_key = key
            if key not in frontmatter:
                frontmatter[key] = []
            continue
        current_key = None
        frontmatter[key] = value

    return frontmatter, body


def load_page_record(path: Path, root: Path) -> PageRecord | None:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    source_path = str(frontmatter.get("source_path", "")).strip()
    category = str(frontmatter.get("category", "")).strip()
    title = str(frontmatter.get("title", "")).strip()
    if not source_path or not category or not title:
        return None
    tags_value = frontmatter.get("tags", [])
    tags = tags_value if isinstance(tags_value, list) else []

    return PageRecord(
        path_abs=path,
        path_rel=path.relative_to(root).as_posix(),
        category=category,
        source_path=source_path,
        source_type=str(frontmatter.get("source_type", "")).strip(),
        title=title,
        status=str(frontmatter.get("status", "")).strip(),
        last_synced=str(frontmatter.get("last_synced", "")).strip(),
        tags=tags,
        body=body,
        frontmatter=frontmatter,
    )


def ensure_structure(root: Path, apply: bool) -> None:
    dirs = [
        root / RAW_DIR,
        root / PAGES_DIR,
        root / PAGES_DIR / "research",
        root / PAGES_DIR / "guides",
        root / PAGES_DIR / "notes",
    ]
    for directory in dirs:
        if apply:
            directory.mkdir(parents=True, exist_ok=True)

    index_path = root / INDEX_FILE
    if apply and not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("# Knowledge Base Index\n\n", encoding="utf-8")
    if apply and not (root / LOG_FILE).exists():
        (root / LOG_FILE).write_text("# Knowledge Base Log\n\n", encoding="utf-8")


def humanize_stem(stem: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", stem)).strip() or stem


def title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return fallback


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug or "document"


def classify_source(title: str, source_rel: str) -> tuple[str, list[str], bool]:
    blob = f"{title} {source_rel}".lower()
    research_keys = ("paper", "research", "study", "report", "arxiv", "experiment")
    guide_keys = ("guide", "how-to", "howto", "comparison", "workflow", "docs", "manual")

    if any(key in blob for key in research_keys):
        return "research", build_tags(title, "research"), False
    if any(key in blob for key in guide_keys):
        return "guides", build_tags(title, "guides"), False
    return "notes", build_tags(title, "notes"), True


def build_tags(title: str, category: str) -> list[str]:
    tokens = [
        tok
        for tok in re.findall(r"[A-Za-z0-9]+", title.lower())
        if len(tok) > 2 and tok not in STOPWORDS
    ]
    tags = []
    for tok in tokens:
        if tok not in tags:
            tags.append(tok)
        if len(tags) >= 6:
            break
    if category not in tags:
        tags.insert(0, category)
    return tags[:8]


def extract_summary(markdown: str) -> str:
    paragraphs = []
    current = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("![") or stripped.startswith("<img"):
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current).strip())

    if not paragraphs:
        return "Extraction completed, but concise summary needs confirmation from the source."

    summary = " ".join(paragraphs[:2]).strip()
    return summary[:900]


def extract_entities(markdown: str, title: str) -> list[str]:
    entities = []
    title_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+.-]{2,}", title)
    for token in title_tokens:
        if token not in entities:
            entities.append(token)
    for token in re.findall(r"\b[A-Z][A-Za-z0-9+.-]{2,}\b", markdown):
        if token not in entities:
            entities.append(token)
        if len(entities) >= 10:
            break
    return entities[:10] if entities else ["to be confirmed"]


def convert_with_project_tool(
    root: Path,
    source_abs: Path,
    output_md: Path,
    media_dir: Path,
) -> None:
    converter = Path(__file__).resolve().parent / "convert_source.py"
    suffix = source_abs.suffix.lower()
    if not converter.exists():
        if suffix in {".md", ".markdown", ".txt"}:
            output_md.write_text(source_abs.read_text(encoding="utf-8"), encoding="utf-8")
            return
        raise RuntimeError(
            f"missing converter at {converter}; cannot process {source_abs.name}"
        )

    cmd = [
        "python3",
        str(converter),
        str(source_abs),
        "-o",
        str(output_md),
        "--media-dir",
        str(media_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or "unknown conversion error"
        raise RuntimeError(stderr)


def remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for sub in sorted(path.rglob("*"), reverse=True):
        if sub.is_file():
            sub.unlink()
        elif sub.is_dir():
            sub.rmdir()
    if path.exists():
        path.rmdir()


def render_page(
    *,
    title: str,
    source_rel: str,
    source_type: str,
    category: str,
    tags: list[str],
    summary: str,
    content_md: str,
    entities: list[str],
    related_lines: list[str],
    classification_pending: bool,
    today: str,
) -> str:
    lines: list[str] = [
        "---",
        f"title: {title}",
        f"source_path: {source_rel}",
        f"source_type: {source_type}",
        f"category: {category}",
        "tags:",
    ]
    for tag in tags:
        lines.append(f"  - {tag}")
    lines.extend(
        [
            "status: generated",
            f"last_synced: {today}",
            "---",
            "",
            f"# {title}",
            "",
            "## Summary",
            summary.strip(),
        ]
    )
    if classification_pending:
        lines.extend(["", "Classification: to be confirmed."])
    lines.extend(
        [
            "",
            "## Content",
            content_md.strip() or "No content extracted.",
            "",
            "## Key Entities",
        ]
    )
    for entity in entities:
        lines.append(f"- {entity}")
    lines.extend(["", "## Related Files Index"])
    if related_lines:
        lines.extend(related_lines)
    else:
        lines.append("- to be confirmed")
    lines.append("")
    return "\n".join(lines)


def tokenize(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[A-Za-z0-9]{3,}", text.lower())
        if tok not in STOPWORDS
    }


def choose_related(target: PageRecord, pages: Iterable[PageRecord]) -> list[str]:
    target_tokens = tokenize(target.title + " " + " ".join(target.tags))
    ranked: list[tuple[int, str, PageRecord]] = []
    for other in pages:
        if other.path_rel == target.path_rel:
            continue
        other_tokens = tokenize(other.title + " " + " ".join(other.tags))
        overlap_set = target_tokens & other_tokens
        overlap = len(overlap_set)
        if overlap <= 0:
            continue
        overlap_terms = ", ".join(sorted(list(overlap_set))[:3])
        reason = (
            f"Shared topic keywords: {overlap_terms}."
            if overlap_terms
            else "Related topic area."
        )
        ranked.append((overlap, reason, other))
    ranked.sort(key=lambda x: (-x[0], x[2].title.lower()))
    return [f"- {item[2].wiki_link} - {item[1]}" for item in ranked[:5]]


def build_index(pages: list[PageRecord]) -> str:
    lines = [
        "# Knowledge Base Index",
        "",
        f"This knowledge base currently contains {len(pages)} generated knowledge pages in the `{PAGES_DIR}/` layer.",
        "",
        "## Document Catalog",
        "",
        "| Title | Category | Source File | Page | Last Synced |",
        "| --- | --- | --- | --- | --- |",
    ]
    for page in sorted(pages, key=lambda p: p.title.lower()):
        source_file = f"`raw/{page.source_path}`"
        lines.append(
            f"| {page.title} | {page.category} | {source_file} | {page.wiki_link} | {page.last_synced or 'to be confirmed'} |"
        )

    lines.extend(["", "## Key Topics"])
    for category in SUPPORTED_CATEGORIES:
        links = [p.wiki_link for p in pages if p.category == category]
        if links:
            lines.append(f"- {category}: {', '.join(links)}")

    lines.extend(["", "## Important Relations"])
    relation_lines: list[str] = []
    for idx, left in enumerate(pages):
        left_tokens = tokenize(left.title + " " + " ".join(left.tags))
        for right in pages[idx + 1 :]:
            overlap = left_tokens & tokenize(right.title + " " + " ".join(right.tags))
            if not overlap:
                continue
            overlap_terms = ", ".join(sorted(list(overlap))[:3])
            relation_lines.append(
                f"- {left.wiki_link} <-> {right.wiki_link}: Shared topics ({overlap_terms})."
            )
    if relation_lines:
        lines.extend(relation_lines[:8])
    else:
        lines.append("- to be confirmed")
    lines.append("")
    return "\n".join(lines)


def append_log(
    root: Path,
    *,
    added: list[PageRecord],
    updated: list[PageRecord],
    deleted: list[str],
    conflicts: list[str],
    apply: bool,
) -> None:
    today = dt.date.today().isoformat()
    log_path = root / LOG_FILE
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# Knowledge Base Log\n\n"
    new_lines: list[str] = [f"## {today}"]

    if added:
        for page in added:
            new_lines.append(
                f"- Added {page.wiki_link} from `raw/{page.source_path}`."
            )
    if updated:
        for page in updated:
            new_lines.append(
                f"- Updated {page.wiki_link} from `raw/{page.source_path}`."
            )
    if deleted:
        for page_rel in deleted:
            new_lines.append(f"- Deleted `{page_rel}` because its source file was removed.")
    if conflicts:
        for conflict in conflicts:
            new_lines.append(f"- Conflict: {conflict}")
    new_lines.append(
        f"- {'Applied' if apply else 'Planned'} incremental sync for knowledge-base structure, index, and relationships."
    )
    block = "\n".join(new_lines) + "\n"

    if f"## {today}" in existing:
        content = existing.rstrip() + "\n" + "\n".join(new_lines[1:]) + "\n"
    else:
        content = existing.rstrip() + "\n\n" + block
    if apply:
        log_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync knowledge base incrementally.")
    parser.add_argument("--root", default=".", help="Knowledge base root directory")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    apply = args.apply
    today = dt.date.today().isoformat()

    ensure_structure(root, apply=apply)

    raw_root = root / RAW_DIR
    pages_root = root / PAGES_DIR
    if not raw_root.exists():
        if apply:
            raw_root.mkdir(parents=True, exist_ok=True)
            pages_root.mkdir(parents=True, exist_ok=True)
            (pages_root / "research").mkdir(parents=True, exist_ok=True)
            (pages_root / "guides").mkdir(parents=True, exist_ok=True)
            (pages_root / "notes").mkdir(parents=True, exist_ok=True)
        else:
            print("mode: dry-run")
            print("environment: greenfield")
            print(f"missing directory: {raw_root}")
            print(
                "No files were modified. Run with --apply to initialize raw/, pages/, "
                "pages/index.md, and log.md."
            )
            return 0

    raw_files = [
        p
        for p in raw_root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_RAW_TYPES
    ]
    raw_by_rel = {p.relative_to(raw_root).as_posix(): p for p in raw_files}

    page_records: list[PageRecord] = []
    for path in pages_root.rglob("*.md"):
        rec = load_page_record(path, root)
        if rec:
            page_records.append(rec)

    source_to_page = {rec.source_path: rec for rec in page_records}
    added_sources = sorted(set(raw_by_rel) - set(source_to_page))
    deleted_sources = sorted(set(source_to_page) - set(raw_by_rel))
    updated_sources: list[str] = []
    for source_rel in sorted(set(source_to_page) & set(raw_by_rel)):
        page_path = source_to_page[source_rel].path_abs
        raw_path = raw_by_rel[source_rel]
        if raw_path.stat().st_mtime > page_path.stat().st_mtime:
            updated_sources.append(source_rel)

    conflicts: list[str] = []
    deleted_page_paths: list[str] = []
    for source_rel in deleted_sources:
        rec = source_to_page[source_rel]
        source_stem = slugify(Path(source_rel).stem)
        maybe_renamed = any(source_stem == slugify(Path(candidate).stem) for candidate in added_sources)
        if maybe_renamed:
            conflicts.append(
                f"possible rename detected for `raw/{source_rel}` -> similar new source; skip deleting `{rec.path_rel}`"
            )
            continue
        deleted_page_paths.append(rec.path_rel)
        if apply and rec.path_abs.exists():
            rec.path_abs.unlink()

    changed_records: list[PageRecord] = []
    converted_failures: list[str] = []
    all_slug_targets = {rec.path_rel for rec in page_records}

    process_sources = [(src, "added") for src in added_sources] + [
        (src, "updated") for src in updated_sources
    ]

    for source_rel, _change_type in process_sources:
        raw_abs = raw_by_rel[source_rel]
        existing = source_to_page.get(source_rel)
        if existing and existing.status != "generated":
            conflicts.append(
                f"manual page detected at `{existing.path_rel}` (status={existing.status}); skipped auto-update"
            )
            continue

        if existing:
            target_category = (
                existing.category if existing.category in SUPPORTED_CATEGORIES else "notes"
            )
            target_slug = existing.path_abs.stem
            target_path = existing.path_abs
            classification_pending = False
        else:
            fallback_title = humanize_stem(raw_abs.stem)
            target_category, _, classification_pending = classify_source(
                fallback_title, source_rel
            )
            target_slug = slugify(fallback_title)
            target_path = root / PAGES_DIR / target_category / f"{target_slug}.md"
            if target_path.relative_to(root).as_posix() in all_slug_targets:
                conflicts.append(
                    f"slug conflict for `raw/{source_rel}` -> `{target_path.relative_to(root).as_posix()}`"
                )
                continue
            all_slug_targets.add(target_path.relative_to(root).as_posix())

        if apply:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_md = target_path.with_suffix(".tmp.md")
            media_dir = target_path.parent / f"{target_path.stem}.assets"
        else:
            dry_dir = Path(tempfile.mkdtemp(prefix="kb-sync-"))
            tmp_md = dry_dir / "converted.md"
            media_dir = dry_dir / "assets"
        try:
            convert_with_project_tool(root, raw_abs, tmp_md, media_dir)
        except Exception as exc:
            converted_failures.append(f"`raw/{source_rel}`: {exc}")
            if tmp_md.exists():
                tmp_md.unlink()
            if not apply:
                remove_tree(tmp_md.parent)
            continue

        converted_text = tmp_md.read_text(encoding="utf-8")
        if tmp_md.exists():
            tmp_md.unlink()
        if not apply:
            remove_tree(tmp_md.parent)

        fallback_title = humanize_stem(raw_abs.stem)
        title = title_from_markdown(converted_text, fallback_title)
        if existing:
            category = target_category
            tags = existing.tags or build_tags(title, category)
            pending = False
        else:
            category = target_category
            tags = build_tags(title, category)
            pending = classification_pending

        entities = extract_entities(converted_text, title)
        summary = extract_summary(converted_text)
        if pending:
            summary = summary + " Classification is to be confirmed."

        placeholder = PageRecord(
            path_abs=target_path,
            path_rel=target_path.relative_to(root).as_posix(),
            category=category,
            source_path=source_rel,
            source_type=raw_abs.suffix.lower().lstrip("."),
            title=title,
            status="generated",
            last_synced=today,
            tags=tags,
            body="",
            frontmatter={},
        )
        related_lines = choose_related(placeholder, page_records + changed_records)
        page_text = render_page(
            title=title,
            source_rel=source_rel,
            source_type=placeholder.source_type,
            category=category,
            tags=tags,
            summary=summary,
            content_md=converted_text,
            entities=entities,
            related_lines=related_lines,
            classification_pending=pending,
            today=today,
        )
        if apply:
            target_path.write_text(page_text, encoding="utf-8")

        new_record = load_page_record(target_path, root) if apply else placeholder
        if new_record:
            changed_records.append(new_record)

    for failure in converted_failures:
        conflicts.append(f"conversion failure: {failure}")

    refreshed_pages: list[PageRecord] = []
    for path in (root / PAGES_DIR).rglob("*.md"):
        record = load_page_record(path, root)
        if record:
            refreshed_pages.append(record)

    if apply:
        index_text = build_index(refreshed_pages)
        (root / INDEX_FILE).write_text(index_text, encoding="utf-8")
        added_records = [r for r in changed_records if r.source_path in added_sources]
        updated_records = [r for r in changed_records if r.source_path in updated_sources]
        append_log(
            root,
            added=added_records,
            updated=updated_records,
            deleted=deleted_page_paths,
            conflicts=conflicts,
            apply=True,
        )

    print(f"mode: {'apply' if apply else 'dry-run'}")
    print(f"added sources: {len(added_sources)}")
    print(f"updated sources: {len(updated_sources)}")
    print(f"deleted sources: {len(deleted_sources)}")
    print(f"processed pages: {len(changed_records)}")
    print(f"conflicts: {len(conflicts)}")
    if conflicts:
        for item in conflicts:
            print(f"- {item}")
    if not apply:
        print("No files were modified. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
