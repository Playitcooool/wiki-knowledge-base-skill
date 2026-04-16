#!/usr/bin/env python3
"""
Incrementally maintain an Obsidian-friendly knowledge base.

This script is intentionally conservative:
- Supports dry-run by default.
- Skips overwriting pages that do not declare `status: generated`.
- Auto-migrates generated pages across unambiguous source renames.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
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
SECTION_MARKERS = (
    "## Summary",
    "## Content",
    "## Key Entities",
    "## Related Files Index",
)


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

    @property
    def assets_dir_abs(self) -> Path:
        return self.path_abs.with_suffix(".assets")

    @property
    def assets_dir_rel(self) -> str:
        return self.assets_dir_abs.relative_to(self.path_abs.parents[2]).as_posix()


@dataclass
class PagePlan:
    source_rel: str
    raw_abs: Path
    existing: PageRecord | None
    target_path: Path
    category: str
    classification_pending: bool
    change_kind: str
    old_source_rel: str | None = None
    old_page_path: Path | None = None
    old_assets_path: Path | None = None
    conversion_text: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)
    source_type: str = ""
    related_lines: list[str] = field(default_factory=list)
    summary: str = ""
    entities: list[str] = field(default_factory=list)

    @property
    def target_rel(self) -> str:
        return self.target_path.relative_to(self.target_path.parents[2]).as_posix()

    @property
    def target_assets_path(self) -> Path:
        return self.target_path.with_suffix(".assets")


@dataclass
class ChangePlan:
    bootstrapped_paths: list[str] = field(default_factory=list)
    added_sources: list[str] = field(default_factory=list)
    updated_sources: list[str] = field(default_factory=list)
    deleted_sources: list[str] = field(default_factory=list)
    renamed_sources: list[str] = field(default_factory=list)
    added_pages: list[str] = field(default_factory=list)
    updated_pages: list[str] = field(default_factory=list)
    renamed_pages: list[str] = field(default_factory=list)
    deleted_pages: list[str] = field(default_factory=list)
    deleted_assets: list[str] = field(default_factory=list)
    skipped_manual_pages: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    page_plans: list[PagePlan] = field(default_factory=list)


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


def desired_bootstrap_paths(root: Path) -> list[Path]:
    return [
        root / RAW_DIR,
        root / PAGES_DIR,
        root / PAGES_DIR / "research",
        root / PAGES_DIR / "guides",
        root / PAGES_DIR / "notes",
        root / INDEX_FILE,
        root / LOG_FILE,
    ]


def ensure_structure(root: Path, apply: bool) -> list[str]:
    created: list[str] = []
    for path in desired_bootstrap_paths(root):
        if path.suffix:
            if apply and not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                initial = (
                    "# Knowledge Base Index\n\n"
                    if path == root / INDEX_FILE
                    else "# Knowledge Base Log\n\n"
                )
                path.write_text(initial, encoding="utf-8")
                created.append(path.relative_to(root).as_posix())
            elif not path.exists():
                created.append(path.relative_to(root).as_posix())
            continue

        if apply and not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(path.relative_to(root).as_posix() + "/")
        elif not path.exists():
            created.append(path.relative_to(root).as_posix() + "/")

    return created


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
    tags: list[str] = []
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

    return " ".join(paragraphs[:2]).strip()[:900]


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


def parse_generated_sections(body: str) -> dict[str, str]:
    sections = {marker: "" for marker in SECTION_MARKERS}
    current: str | None = None
    buffer: list[str] = []
    for line in body.splitlines():
        if line in SECTION_MARKERS:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = line
            buffer = []
            continue
        if current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def rebuild_generated_pages(root: Path, today: str) -> list[PageRecord]:
    pages: list[PageRecord] = []
    for path in (root / PAGES_DIR).rglob("*.md"):
        record = load_page_record(path, root)
        if record:
            pages.append(record)

    generated_pages = [page for page in pages if page.status == "generated"]
    for page in generated_pages:
        sections = parse_generated_sections(page.body)
        entities = []
        for line in sections["## Key Entities"].splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                entities.append(stripped[2:])
        related_lines = choose_related(page, generated_pages)
        rebuilt = render_page(
            title=page.title,
            source_rel=page.source_path,
            source_type=page.source_type,
            category=page.category,
            tags=page.tags,
            summary=sections["## Summary"] or extract_summary(sections["## Content"]),
            content_md=sections["## Content"] or "No content extracted.",
            entities=entities or ["to be confirmed"],
            related_lines=related_lines,
            classification_pending="Classification: to be confirmed." in sections["## Summary"],
            today=today,
        )
        page.path_abs.write_text(rebuilt, encoding="utf-8")

    refreshed: list[PageRecord] = []
    for path in (root / PAGES_DIR).rglob("*.md"):
        record = load_page_record(path, root)
        if record:
            refreshed.append(record)
    return refreshed


def append_log(
    root: Path,
    *,
    added: list[PageRecord],
    updated: list[PageRecord],
    renamed: list[str],
    deleted: list[str],
    deleted_assets: list[str],
    conflicts: list[str],
) -> None:
    today = dt.date.today().isoformat()
    log_path = root / LOG_FILE
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# Knowledge Base Log\n\n"
    new_lines: list[str] = [f"## {today}"]

    for page in added:
        new_lines.append(f"- Added {page.wiki_link} from `raw/{page.source_path}`.")
    for page in updated:
        new_lines.append(f"- Updated {page.wiki_link} from `raw/{page.source_path}`.")
    for rename in renamed:
        new_lines.append(f"- Renamed source mapping: {rename}.")
    for page_rel in deleted:
        new_lines.append(f"- Deleted `{page_rel}` because its source file was removed.")
    for assets_rel in deleted_assets:
        new_lines.append(f"- Deleted asset directory `{assets_rel}` because its page was removed.")
    for conflict in conflicts:
        new_lines.append(f"- Conflict: {conflict}")
    new_lines.append("- Applied incremental sync for knowledge-base structure, index, and relationships.")
    block = "\n".join(new_lines) + "\n"

    if f"## {today}" in existing:
        content = existing.rstrip() + "\n" + "\n".join(new_lines[1:]) + "\n"
    else:
        content = existing.rstrip() + "\n\n" + block
    log_path.write_text(content, encoding="utf-8")


def canonical_target_path(root: Path, source_rel: str, existing: PageRecord | None) -> tuple[Path, str, bool]:
    if existing:
        category = existing.category if existing.category in SUPPORTED_CATEGORIES else "notes"
        return root / existing.path_rel, category, False

    fallback_title = humanize_stem(Path(source_rel).stem)
    category, _, pending = classify_source(fallback_title, source_rel)
    slug = slugify(fallback_title)
    return root / PAGES_DIR / category / f"{slug}.md", category, pending


def detect_rename_pairs(
    added_sources: list[str],
    deleted_sources: list[str],
    source_to_page: dict[str, PageRecord],
) -> tuple[dict[str, str], list[str]]:
    renames: dict[str, str] = {}
    conflicts: list[str] = []
    stem_to_added: dict[str, list[str]] = {}
    stem_to_deleted: dict[str, list[str]] = {}

    for source_rel in added_sources:
        stem_to_added.setdefault(slugify(Path(source_rel).stem), []).append(source_rel)
    for source_rel in deleted_sources:
        stem_to_deleted.setdefault(slugify(Path(source_rel).stem), []).append(source_rel)

    for stem, deleted_items in stem_to_deleted.items():
        added_items = stem_to_added.get(stem, [])
        if not added_items:
            continue
        if len(added_items) == 1 and len(deleted_items) == 1:
            deleted_source = deleted_items[0]
            page = source_to_page[deleted_source]
            if page.status != "generated":
                conflicts.append(
                    f"manual page detected at `{page.path_rel}` (status={page.status}); skipped auto-rename from `raw/{deleted_source}`"
                )
                continue
            renames[deleted_source] = added_items[0]
            continue

        for deleted_source in deleted_items:
            page = source_to_page[deleted_source]
            conflicts.append(
                f"ambiguous rename detected for `raw/{deleted_source}` affecting `{page.path_rel}`; manual review required"
            )
    return renames, conflicts


def convert_for_plan(root: Path, raw_abs: Path, target_path: Path, apply: bool) -> tuple[str, Path]:
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
        text = tmp_md.read_text(encoding="utf-8")
    finally:
        if tmp_md.exists():
            tmp_md.unlink()
        if not apply:
            remove_tree(tmp_md.parent)
    return text, media_dir


def build_change_plan(root: Path, apply: bool, today: str) -> ChangePlan:
    plan = ChangePlan()
    raw_root = root / RAW_DIR
    pages_root = root / PAGES_DIR
    plan.bootstrapped_paths = ensure_structure(root, apply=False)

    if not raw_root.exists():
        return plan

    raw_files = [
        path
        for path in raw_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_RAW_TYPES
    ]
    raw_by_rel = {path.relative_to(raw_root).as_posix(): path for path in raw_files}

    page_records: list[PageRecord] = []
    if pages_root.exists():
        for path in pages_root.rglob("*.md"):
            record = load_page_record(path, root)
            if record:
                page_records.append(record)
    source_to_page = {record.source_path: record for record in page_records}

    added_sources = sorted(set(raw_by_rel) - set(source_to_page))
    deleted_sources = sorted(set(source_to_page) - set(raw_by_rel))
    updated_sources = sorted(
        source_rel
        for source_rel in set(source_to_page) & set(raw_by_rel)
        if raw_by_rel[source_rel].stat().st_mtime > source_to_page[source_rel].path_abs.stat().st_mtime
    )
    rename_pairs, rename_conflicts = detect_rename_pairs(added_sources, deleted_sources, source_to_page)
    plan.conflicts.extend(rename_conflicts)

    rename_new_sources = set(rename_pairs.values())
    rename_old_sources = set(rename_pairs.keys())
    plan.added_sources = [item for item in added_sources if item not in rename_new_sources]
    plan.deleted_sources = [item for item in deleted_sources if item not in rename_old_sources]
    plan.updated_sources = updated_sources
    plan.renamed_sources = [
        f"raw/{old} -> raw/{new}" for old, new in sorted(rename_pairs.items())
    ]

    for source_rel in plan.deleted_sources:
        page = source_to_page[source_rel]
        if page.status != "generated":
            plan.skipped_manual_pages.append(page.path_rel)
            plan.conflicts.append(
                f"manual page detected at `{page.path_rel}` (status={page.status}); skipped deletion after `raw/{source_rel}` disappeared"
            )
            continue
        plan.deleted_pages.append(page.path_rel)
        if page.assets_dir_abs.exists():
            plan.deleted_assets.append(page.assets_dir_abs.relative_to(root).as_posix())

    all_targets = {record.path_rel for record in page_records}
    process_items: list[tuple[str, str, str | None]] = []
    process_items.extend(("add", source_rel, None) for source_rel in plan.added_sources)
    process_items.extend(("update", source_rel, None) for source_rel in plan.updated_sources)
    process_items.extend(("rename", new_source, old_source) for old_source, new_source in sorted(rename_pairs.items()))

    placeholder_records = list(page_records)
    for change_kind, source_rel, old_source_rel in process_items:
        raw_abs = raw_by_rel[source_rel]
        existing = source_to_page.get(old_source_rel or source_rel)
        if existing and existing.status != "generated":
            plan.skipped_manual_pages.append(existing.path_rel)
            plan.conflicts.append(
                f"manual page detected at `{existing.path_rel}` (status={existing.status}); skipped auto-update"
            )
            continue

        target_path, category, classification_pending = canonical_target_path(root, source_rel, existing)
        target_rel = target_path.relative_to(root).as_posix()
        if existing is None and target_rel in all_targets:
            plan.conflicts.append(f"slug conflict for `raw/{source_rel}` -> `{target_rel}`")
            continue
        all_targets.add(target_rel)

        try:
            converted_text, _media_dir = convert_for_plan(root, raw_abs, target_path, apply=False)
        except Exception as exc:
            plan.conflicts.append(f"conversion failure: `raw/{source_rel}`: {exc}")
            continue

        fallback_title = humanize_stem(raw_abs.stem)
        title = title_from_markdown(converted_text, fallback_title)
        tags = existing.tags if existing and existing.tags else build_tags(title, category)
        summary = extract_summary(converted_text)
        pending = classification_pending and existing is None
        if pending:
            summary = summary + " Classification is to be confirmed."
        entities = extract_entities(converted_text, title)

        plan_item = PagePlan(
            source_rel=source_rel,
            raw_abs=raw_abs,
            existing=existing,
            target_path=target_path,
            category=category,
            classification_pending=pending,
            change_kind=change_kind,
            old_source_rel=old_source_rel,
            old_page_path=existing.path_abs if existing else None,
            old_assets_path=existing.assets_dir_abs if existing else None,
            conversion_text=converted_text,
            title=title,
            tags=tags,
            source_type=raw_abs.suffix.lower().lstrip("."),
            summary=summary,
            entities=entities,
        )
        placeholder = PageRecord(
            path_abs=target_path,
            path_rel=target_rel,
            category=category,
            source_path=source_rel,
            source_type=plan_item.source_type,
            title=title,
            status="generated",
            last_synced=today,
            tags=tags,
            body="",
            frontmatter={},
        )
        placeholder_records.append(placeholder)
        plan.page_plans.append(plan_item)

        if change_kind == "add":
            plan.added_pages.append(target_rel)
        elif change_kind == "update":
            plan.updated_pages.append(target_rel)
        else:
            old_page_rel = existing.path_rel if existing else target_rel
            plan.renamed_pages.append(f"{old_page_rel} -> {target_rel}")
            if old_page_rel != target_rel and existing and existing.assets_dir_abs.exists():
                plan.deleted_assets.append(existing.assets_dir_abs.relative_to(root).as_posix())

    for page_plan in plan.page_plans:
        placeholder = PageRecord(
            path_abs=page_plan.target_path,
            path_rel=page_plan.target_path.relative_to(root).as_posix(),
            category=page_plan.category,
            source_path=page_plan.source_rel,
            source_type=page_plan.source_type,
            title=page_plan.title,
            status="generated",
            last_synced=today,
            tags=page_plan.tags,
            body="",
            frontmatter={},
        )
        related_pool = [
            PageRecord(
                path_abs=item.target_path,
                path_rel=item.target_path.relative_to(root).as_posix(),
                category=item.category,
                source_path=item.source_rel,
                source_type=item.source_type,
                title=item.title,
                status="generated",
                last_synced=today,
                tags=item.tags,
                body="",
                frontmatter={},
            )
            for item in plan.page_plans
        ] + [record for record in page_records if record.status == "generated"]
        page_plan.related_lines = choose_related(placeholder, related_pool)

    return plan


def print_group(label: str, items: list[str]) -> None:
    print(f"{label}: {len(items)}")
    for item in items:
        print(f"- {item}")


def execute_apply(root: Path, plan: ChangePlan, today: str) -> list[PageRecord]:
    created_bootstrap = ensure_structure(root, apply=True)
    if created_bootstrap:
        plan.bootstrapped_paths = created_bootstrap

    source_to_written_page: dict[str, PageRecord] = {}

    for page_rel in plan.deleted_pages:
        page_path = root / page_rel
        if page_path.exists():
            page_path.unlink()
    for assets_rel in plan.deleted_assets:
        assets_path = root / assets_rel
        if assets_path.exists():
            remove_tree(assets_path)

    for page_plan in plan.page_plans:
        old_path = page_plan.old_page_path
        if page_plan.change_kind == "rename" and old_path and old_path != page_plan.target_path:
            if old_path.exists():
                page_plan.target_path.parent.mkdir(parents=True, exist_ok=True)
                old_path.replace(page_plan.target_path)
            if page_plan.old_assets_path and page_plan.old_assets_path.exists():
                page_plan.target_assets_path.parent.mkdir(parents=True, exist_ok=True)
                page_plan.old_assets_path.replace(page_plan.target_assets_path)

        page_plan.target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_md = page_plan.target_path.with_suffix(".tmp.md")
        media_dir = page_plan.target_assets_path
        convert_with_project_tool(root, page_plan.raw_abs, tmp_md, media_dir)
        converted_text = tmp_md.read_text(encoding="utf-8")
        tmp_md.unlink()

        fallback_title = humanize_stem(page_plan.raw_abs.stem)
        title = title_from_markdown(converted_text, fallback_title)
        tags = page_plan.tags or build_tags(title, page_plan.category)
        summary = extract_summary(converted_text)
        if page_plan.classification_pending:
            summary = summary + " Classification is to be confirmed."
        entities = extract_entities(converted_text, title)
        page_text = render_page(
            title=title,
            source_rel=page_plan.source_rel,
            source_type=page_plan.source_type,
            category=page_plan.category,
            tags=tags,
            summary=summary,
            content_md=converted_text,
            entities=entities,
            related_lines=page_plan.related_lines,
            classification_pending=page_plan.classification_pending,
            today=today,
        )
        page_plan.target_path.write_text(page_text, encoding="utf-8")
        record = load_page_record(page_plan.target_path, root)
        if record:
            source_to_written_page[page_plan.source_rel] = record

    refreshed_pages = rebuild_generated_pages(root, today)
    index_text = build_index(refreshed_pages)
    (root / INDEX_FILE).write_text(index_text, encoding="utf-8")

    added_records = [source_to_written_page[source] for source in plan.added_sources if source in source_to_written_page]
    updated_records = [source_to_written_page[source] for source in plan.updated_sources if source in source_to_written_page]
    append_log(
        root,
        added=added_records,
        updated=updated_records,
        renamed=plan.renamed_sources,
        deleted=plan.deleted_pages,
        deleted_assets=plan.deleted_assets,
        conflicts=plan.conflicts,
    )
    return refreshed_pages


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync knowledge base incrementally.")
    parser.add_argument("--root", default=".", help="Knowledge base root directory")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    apply = args.apply
    today = dt.date.today().isoformat()

    plan = build_change_plan(root, apply=apply, today=today)

    raw_root = root / RAW_DIR
    if not raw_root.exists():
        print("mode: dry-run" if not apply else "mode: apply")
        print("environment: greenfield")
        print(f"missing directory: {raw_root}")
        print_group("bootstrapped paths", plan.bootstrapped_paths)
        if not apply:
            print("No files were modified. Run with --apply to initialize raw/, pages/, pages/index.md, and log.md.")
            return 0
        ensure_structure(root, apply=True)
        return 0

    if apply:
        execute_apply(root, plan, today)

    print(f"mode: {'apply' if apply else 'dry-run'}")
    print_group("bootstrapped paths", plan.bootstrapped_paths if (not raw_root.exists() or apply) else [])
    print_group("added sources", plan.added_sources)
    print_group("updated sources", plan.updated_sources)
    print_group("deleted sources", plan.deleted_sources)
    print_group("renamed sources", plan.renamed_sources)
    print_group("added pages", plan.added_pages)
    print_group("updated pages", plan.updated_pages)
    print_group("renamed pages", plan.renamed_pages)
    print_group("deleted pages", plan.deleted_pages)
    print_group("deleted assets", plan.deleted_assets)
    print_group("skipped manual pages", sorted(dict.fromkeys(plan.skipped_manual_pages)))
    print_group("conflicts", plan.conflicts)
    if not apply:
        print("No files were modified. Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
