from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INGEST_SCRIPT = REPO_ROOT / "skills/knowledge-base-maintainer/scripts/kb-ingest.py"
DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "commands/ingest.md",
    REPO_ROOT / "skills/knowledge-base-maintainer/SKILL.md",
    REPO_ROOT / "skills/knowledge-base-maintainer/references/workflow.md",
]
REAL_SCRIPT_PREFIX = "skills/knowledge-base-maintainer/scripts/"
INTERACTION_DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "commands/ingest.md",
    REPO_ROOT / "skills/knowledge-base-maintainer/SKILL.md",
    REPO_ROOT / "skills/knowledge-base-maintainer/references/workflow.md",
]
AGENT_PROMPT_PATH = REPO_ROOT / "skills/knowledge-base-maintainer/agents/openai.yaml"
CURSOR_PLUGIN_MANIFEST = REPO_ROOT / ".cursor-plugin/plugin.json"
LEGACY_PLUGIN_DIR = REPO_ROOT / "plugins/kb"


def run_ingest(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(INGEST_SCRIPT), "--root", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class SyncKbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="kb-sync-tests-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_greenfield_preview_lists_bootstrap_targets_without_writing(self) -> None:
        result = run_ingest(self.temp_dir)

        self.assertEqual(result.returncode, 0)
        self.assertIn("mode: dry-run", result.stdout)
        self.assertIn("environment: greenfield", result.stdout)
        self.assertIn("bootstrapped paths:", result.stdout)
        self.assertIn("- raw/", result.stdout)
        self.assertIn("- pages/index.md", result.stdout)
        self.assertFalse((self.temp_dir / "raw").exists())

    def test_greenfield_apply_bootstraps_and_reports_paths(self) -> None:
        result = run_ingest(self.temp_dir, "--apply")

        self.assertEqual(result.returncode, 0)
        self.assertIn("mode: apply", result.stdout)
        self.assertIn("bootstrapped paths:", result.stdout)
        self.assertTrue((self.temp_dir / "raw").is_dir())
        self.assertTrue((self.temp_dir / "pages/research").is_dir())
        self.assertTrue((self.temp_dir / "pages/index.md").is_file())
        self.assertTrue((self.temp_dir / "log.md").is_file())

    def test_rename_is_auto_migrated_for_generated_page(self) -> None:
        write_text(
            self.temp_dir / "raw/research-paper.md",
            "# Research Paper\n\nThis study explores retrieval augmented generation.\n",
        )
        apply_first = run_ingest(self.temp_dir, "--apply")
        self.assertEqual(apply_first.returncode, 0)

        old_source = self.temp_dir / "raw/research-paper.md"
        renamed_source = self.temp_dir / "raw/research_paper.txt"
        old_source.rename(renamed_source)

        preview = run_ingest(self.temp_dir)
        self.assertEqual(preview.returncode, 0)
        self.assertIn("renamed sources: 1", preview.stdout)
        self.assertIn("- raw/research-paper.md -> raw/research_paper.txt", preview.stdout)
        self.assertNotIn("slug conflict", preview.stdout)

        apply_second = run_ingest(self.temp_dir, "--apply")
        self.assertEqual(apply_second.returncode, 0)
        page_text = (self.temp_dir / "pages/research/research-paper.md").read_text(encoding="utf-8")
        self.assertIn("source_path: research_paper.txt", page_text)
        self.assertFalse((self.temp_dir / "pages/research/research_paper.md").exists())

    def test_related_files_are_backfilled_for_existing_pages(self) -> None:
        write_text(
            self.temp_dir / "raw/vector-search-guide.md",
            "# Vector Search Guide\n\nThis guide explains vector search and embeddings for retrieval.\n",
        )
        self.assertEqual(run_ingest(self.temp_dir, "--apply").returncode, 0)

        write_text(
            self.temp_dir / "raw/embeddings-search-comparison.md",
            "# Embeddings Search Comparison\n\nThis guide compares embeddings and vector search workflows.\n",
        )
        self.assertEqual(run_ingest(self.temp_dir, "--apply").returncode, 0)

        first_page = (self.temp_dir / "pages/guides/vector-search-guide.md").read_text(encoding="utf-8")
        second_page = (
            self.temp_dir / "pages/guides/embeddings-search-comparison.md"
        ).read_text(encoding="utf-8")
        self.assertIn("[[pages/guides/embeddings-search-comparison]]", first_page)
        self.assertIn("[[pages/guides/vector-search-guide]]", second_page)

    def test_delete_removes_generated_page_and_assets(self) -> None:
        write_text(
            self.temp_dir / "raw/research-paper.md",
            "# Research Paper\n\nThis study explores retrieval augmented generation.\n",
        )
        self.assertEqual(run_ingest(self.temp_dir, "--apply").returncode, 0)

        assets_dir = self.temp_dir / "pages/research/research-paper.assets"
        assets_dir.mkdir(parents=True)
        write_text(assets_dir / "figure.txt", "asset\n")

        os.remove(self.temp_dir / "raw/research-paper.md")
        result = run_ingest(self.temp_dir, "--apply")

        self.assertEqual(result.returncode, 0)
        self.assertIn("deleted pages: 1", result.stdout)
        self.assertIn("- pages/research/research-paper.md", result.stdout)
        self.assertFalse((self.temp_dir / "pages/research/research-paper.md").exists())
        self.assertFalse(assets_dir.exists())

    def test_manual_page_is_reported_as_skipped(self) -> None:
        write_text(
            self.temp_dir / "raw/draft.md",
            "# Draft Source\n\nUser updated source text.\n",
        )
        write_text(
            self.temp_dir / "pages/notes/draft-source.md",
            textwrap.dedent(
                """\
                ---
                title: Draft Source
                source_path: draft.md
                source_type: md
                category: notes
                tags:
                  - notes
                status: curated
                last_synced: 2026-04-15
                ---

                # Draft Source

                ## Summary
                Manual summary.
                """
            ),
        )
        time.sleep(1.1)
        write_text(
            self.temp_dir / "raw/draft.md",
            "# Draft Source\n\nUser updated source text, version two.\n",
        )

        result = run_ingest(self.temp_dir)
        self.assertEqual(result.returncode, 0)
        self.assertIn("skipped manual pages: 1", result.stdout)
        self.assertIn("- pages/notes/draft-source.md", result.stdout)

    def test_docs_reference_real_script_paths(self) -> None:
        for path in DOC_PATHS:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("python3 scripts/kb-ingest.py", text, msg=str(path))
            self.assertNotIn("python3 scripts/doctor.py", text, msg=str(path))
            self.assertIn(REAL_SCRIPT_PREFIX, text, msg=str(path))

    def test_ingest_docs_describe_check_first_then_auto_apply_or_ask(self) -> None:
        required_phrases = [
            "always check",
            "auto-apply",
            "ask",
            "delete",
            "confirm",
        ]
        for path in INTERACTION_DOC_PATHS:
            text = path.read_text(encoding="utf-8").lower()
            for phrase in required_phrases:
                self.assertIn(phrase, text, msg=f"{path} missing {phrase!r}")

    def test_agent_prompt_says_check_first_and_ask_on_risk(self) -> None:
        text = AGENT_PROMPT_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("check what would change first", text)
        self.assertIn("auto-apply", text)
        self.assertIn("ask", text)
        self.assertIn("delete", text)

    def test_cursor_plugin_manifest_and_docs_exist_for_local_support(self) -> None:
        self.assertTrue(CURSOR_PLUGIN_MANIFEST.is_file())

        manifest_text = CURSOR_PLUGIN_MANIFEST.read_text(encoding="utf-8")
        self.assertIn('"name": "kb"', manifest_text)
        self.assertIn('"skills": "./skills/"', manifest_text)
        self.assertIn('"commands": "./commands/"', manifest_text)

        readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("#### Cursor", readme_text)
        self.assertIn("/kb:ingest", readme_text)
        self.assertIn("not published in Cursor Marketplace yet", readme_text)

    def test_legacy_nested_plugin_package_has_been_removed(self) -> None:
        self.assertFalse(LEGACY_PLUGIN_DIR.exists())
        for path in DOC_PATHS + INTERACTION_DOC_PATHS:
            self.assertNotIn("plugins/kb/", str(path))


if __name__ == "__main__":
    unittest.main()
