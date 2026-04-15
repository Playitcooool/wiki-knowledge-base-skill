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
    checks = [
        ("pandoc", bool(shutil.which("pandoc")), "DOCX/HTML -> Markdown (+ media)"),
        ("textutil", bool(shutil.which("textutil")), "macOS document utility"),
        ("docling", bool(shutil.which("docling")), "Preferred PDF conversion backend"),
        ("mineru", bool(shutil.which("mineru")), "Fallback PDF conversion backend"),
        ("pypdf", has_python_module("pypdf"), "Final PDF text/image fallback"),
    ]

    print("Knowledge Base Tool Doctor")
    print()
    for label, ok, detail in checks:
        print(status_line(label, ok, detail))

    print()
    print("Project defaults:")
    print("- DOCX -> Markdown: pandoc with media extraction")
    print("- PDF -> Markdown: Docling (default) -> MinerU (fallback) -> pypdf (last fallback)")
    print("- Scanned PDF OCR: handled by Docling/MinerU when installed")

    essential_ok = checks[0][1] and checks[1][1] and checks[4][1]
    return 0 if essential_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
