#!/usr/bin/env python3
"""
Report local conversion-tool availability for this knowledge-base project.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys


def has_python_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def status_line(label: str, ok: bool, detail: str) -> str:
    state = "OK" if ok else "MISSING"
    return f"{label:<16} {state:<8} {detail}"


def main() -> int:
    pandoc_ok = bool(shutil.which("pandoc"))
    docling_ok = bool(shutil.which("docling"))
    mineru_ok = bool(shutil.which("mineru"))
    pypdf_ok = has_python_module("pypdf")

    checks = [
        ("pandoc", pandoc_ok, "DOCX/HTML -> Markdown (+ media)"),
        ("docling", docling_ok, "Preferred PDF conversion backend"),
        ("mineru", mineru_ok, "Fallback PDF conversion backend"),
        ("pypdf", pypdf_ok, "Final PDF text/image fallback"),
    ]

    print("Knowledge Base Tool Doctor")
    print()
    for label, ok, detail in checks:
        print(status_line(label, ok, detail))

    print()
    print("Project defaults:")
    print("- Single entrypoint: run /kb:ingest, then inspect capability guidance only if conversion is blocked")
    print("- Base support: md/txt ingestion + basic PDF fallback")
    print("- On-demand support: DOCX/HTML import via pandoc")
    print("- Enhanced PDF path: Docling (default) -> MinerU (fallback) -> pypdf (last fallback)")
    print("- Scanned PDF OCR: available only when Docling or MinerU is installed")
    print()
    print("Capability tiers:")
    print("- Out of the box: md/txt ingestion works without extra dependencies")
    print(
        "- Base support: "
        + ("md/txt ingestion + basic PDF fallback" if pypdf_ok else "install `pip install -r requirements.txt` for basic PDF fallback")
    )
    print(
        "- On-demand DOCX support: "
        + ("ready" if pandoc_ok else "install pandoc")
    )
    print(
        "- Enhanced OCR PDF support: "
        + ("ready" if docling_ok or mineru_ok else "pip install -r requirements-optional.txt")
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
