#!/usr/bin/env python3
"""
Convert raw source files into Markdown suitable for page generation.

Supported inputs:
- .md / .markdown / .txt
- .html / .htm
- .docx
- .pdf

Local-first strategy:
- DOCX and HTML: pandoc
- PDF: pypdf text extraction

This script only performs source conversion. It does not update pages/,
index.md, or log.md.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
PANDOC_EXTENSIONS = {".docx", ".html", ".htm"}
PDF_EXTENSIONS = {".pdf"}


class ConversionError(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaConfig:
    media_dir: Path
    reference_dir: Path


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sanitize_path_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return cleaned or "source"


def to_markdown_path(path: Path, reference_dir: Path) -> str:
    try:
        relative = os.path.relpath(path, start=reference_dir)
    except ValueError:
        return path.as_posix()
    return Path(relative).as_posix()


def resolve_media_config(
    input_path: Path,
    output_path: Path | None,
    media_dir_arg: str | None,
) -> MediaConfig:
    reference_dir = (output_path.parent if output_path else Path.cwd()).resolve()

    if media_dir_arg:
        media_dir = Path(media_dir_arg).expanduser()
        if not media_dir.is_absolute():
            media_dir = (Path.cwd() / media_dir).resolve()
    elif output_path:
        media_dir = (output_path.parent / f"{output_path.stem}.assets").resolve()
    else:
        media_dir = (
            Path.cwd()
            / ".converted_media"
            / sanitize_path_component(input_path.stem)
        ).resolve()

    return MediaConfig(media_dir=media_dir, reference_dir=reference_dir)


def run_pandoc(
    input_path: Path,
    from_format: str | None = None,
    media_config: MediaConfig | None = None,
) -> str:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise ConversionError(
            "pandoc is required for this file type but is not installed locally."
        )

    working_dir = media_config.reference_dir if media_config else Path.cwd()
    cmd = [
        pandoc,
        to_markdown_path(input_path, working_dir),
        "--to",
        "gfm+pipe_tables",
        "--wrap=none",
    ]
    if from_format:
        cmd.extend(["--from", from_format])
    if media_config:
        media_config.media_dir.mkdir(parents=True, exist_ok=True)
        cmd.append(
            f"--extract-media={to_markdown_path(media_config.media_dir, working_dir)}"
        )

    result = subprocess.run(
        cmd,
        check=False,
        cwd=working_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown pandoc error"
        raise ConversionError(f"pandoc conversion failed: {stderr}")
    return result.stdout


def normalize_extracted_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []
    blank_run = 0

    for line in lines:
        if line.strip():
            blank_run = 0
            cleaned.append(line)
            continue

        blank_run += 1
        if blank_run <= 1:
            cleaned.append("")

    return "\n".join(cleaned).strip() + "\n"


def normalize_image_extension(name: str) -> str:
    suffix = Path(name).suffix.lower()
    if suffix and re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        return suffix
    return ".bin"


def extract_pdf_images(page, page_number: int, media_config: MediaConfig) -> list[str]:
    page_images = list(page.images)
    if not page_images:
        return []

    image_dir = media_config.media_dir / "media"
    image_dir.mkdir(parents=True, exist_ok=True)

    markdown_images: list[str] = []
    for image_index, image in enumerate(page_images, start=1):
        extension = normalize_image_extension(image.name)
        filename = f"page-{page_number:03d}-image-{image_index:02d}{extension}"
        image_path = image_dir / filename
        image_path.write_bytes(image.data)
        image_ref = to_markdown_path(image_path, media_config.reference_dir)
        markdown_images.append(f"![Page {page_number} image {image_index}]({image_ref})")

    return markdown_images


def convert_pdf(path: Path, media_config: MediaConfig) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - library raises mixed errors
        raise ConversionError(f"failed to open PDF: {exc}") from exc

    page_sections: list[str] = []
    extracted_chars = 0
    extracted_images = 0
    image_errors: list[tuple[int, str]] = []

    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - mixed parser errors
            raise ConversionError(f"failed to extract text from page {idx}: {exc}") from exc

        text = normalize_extracted_text(text)
        extracted_chars += len(text.strip())

        image_note = None
        try:
            image_markdown = extract_pdf_images(page, idx, media_config)
        except Exception as exc:  # pragma: no cover - mixed parser errors
            image_markdown = []
            image_note = f"> Note: Image extraction failed on this page: {exc}"
            image_errors.append((idx, str(exc)))

        extracted_images += len(image_markdown)

        section_parts = [
            f"## Page {idx}",
            text or "[No extractable text found on this page.]\n",
        ]
        if image_note:
            section_parts.append(image_note)
        if image_markdown:
            section_parts.append("### Images")
            section_parts.extend(image_markdown)

        page_sections.append("\n\n".join(section_parts))

    if extracted_chars < 100 and extracted_images == 0:
        if image_errors:
            failed_pages = ", ".join(str(page_no) for page_no, _ in image_errors)
            raise ConversionError(
                "PDF text extraction returned very little text, and embedded image "
                f"extraction failed on page(s) {failed_pages}. The file may be "
                "scanned or use an unsupported image encoding; OCR is not configured."
            )
        raise ConversionError(
            "PDF text extraction returned very little text. The file may be scanned "
            "or image-based and likely needs OCR, which is not configured in this project yet."
        )

    markdown = "\n\n".join(page_sections).strip() + "\n"
    if extracted_chars < 100 and extracted_images > 0:
        note = (
            "> Note: Extracted text was very limited. This PDF appears to be mostly "
            "image-based. Embedded images were exported, but OCR is not configured.\n\n"
        )
        return note + markdown

    return markdown


def convert_source(
    path: Path,
    output_path: Path | None = None,
    media_dir_arg: str | None = None,
) -> str:
    suffix = path.suffix.lower()
    media_config = resolve_media_config(path, output_path, media_dir_arg)

    if suffix in TEXT_EXTENSIONS:
        return normalize_extracted_text(read_text_file(path))

    if suffix == ".docx":
        return run_pandoc(path, from_format="docx", media_config=media_config)

    if suffix in {".html", ".htm"}:
        return run_pandoc(path, from_format="html")

    if suffix in PDF_EXTENSIONS:
        return convert_pdf(path, media_config=media_config)

    raise ConversionError(
        f"unsupported source type: {suffix or '[no extension]'}. "
        "Supported types: .md, .markdown, .txt, .html, .htm, .docx, .pdf"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a raw source file into Markdown."
    )
    parser.add_argument("input", help="Input source file path")
    parser.add_argument(
        "-o",
        "--output",
        help="Output Markdown file path. If omitted, writes to stdout.",
    )
    parser.add_argument(
        "--media-dir",
        help=(
            "Directory for extracted media. Defaults to <output-stem>.assets when "
            "--output is set, otherwise .converted_media/<input-stem> in the cwd."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else None
    )

    try:
        markdown = convert_source(
            input_path,
            output_path=output_path,
            media_dir_arg=args.media_dir,
        )
    except ConversionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
