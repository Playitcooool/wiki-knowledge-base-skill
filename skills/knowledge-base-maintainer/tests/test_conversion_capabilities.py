import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONVERT_SOURCE_PATH = ROOT / "scripts" / "convert_source.py"
DOCTOR_PATH = ROOT / "scripts" / "doctor.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ConversionCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.convert_source = load_module("kb_convert_source", CONVERT_SOURCE_PATH)
        cls.doctor = load_module("kb_doctor", DOCTOR_PATH)

    def test_docx_missing_support_message_is_capability_based(self):
        with mock.patch.object(self.convert_source.shutil, "which", return_value=None):
            with self.assertRaisesRegex(
                self.convert_source.ConversionError,
                "DOCX support is not installed",
                ):
                    self.convert_source.run_pandoc(
                        Path("/tmp/example.docx"),
                        from_format="docx",
                    )

    def test_markitdown_missing_blocks_rich_document_ingestion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "example.docx"
            source.write_bytes(b"placeholder")
            with mock.patch.dict("sys.modules", {"markitdown": None}):
                with self.assertRaisesRegex(
                    self.convert_source.ConversionError,
                    "MarkItDown rich-document support is not installed",
                ):
                    self.convert_source.convert_source(source)

    def test_docx_uses_markitdown_before_pandoc(self):
        fake_module = type("FakeModule", (), {})()

        class FakeResult:
            text_content = "# Converted by MarkItDown\n\nHello\n"

        class FakeMarkItDown:
            def __init__(self, enable_plugins=False):
                self.enable_plugins = enable_plugins

            def convert(self, path):
                return FakeResult()

        fake_module.MarkItDown = FakeMarkItDown

        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "example.docx"
            source.write_bytes(b"placeholder")
            with mock.patch.dict("sys.modules", {"markitdown": fake_module}):
                with mock.patch.object(self.convert_source, "run_pandoc") as run_pandoc:
                    result = self.convert_source.convert_source(source)
        self.assertIn("Converted by MarkItDown", result)
        run_pandoc.assert_not_called()

    def test_pdf_falls_back_when_markitdown_output_is_too_thin(self):
        fake_module = type("FakeModule", (), {})()

        class FakeResult:
            text_content = "tiny"

        class FakeMarkItDown:
            def __init__(self, enable_plugins=False):
                self.enable_plugins = enable_plugins

            def convert(self, path):
                return FakeResult()

        fake_module.MarkItDown = FakeMarkItDown

        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "example.pdf"
            source.write_bytes(b"%PDF-1.4")
            with mock.patch.dict("sys.modules", {"markitdown": fake_module}):
                with mock.patch.object(
                    self.convert_source,
                    "convert_pdf_with_backends",
                    return_value="fallback output\n",
                ) as fallback:
                    result = self.convert_source.convert_source(source)

        self.assertEqual(result, "fallback output\n")
        fallback.assert_called_once()

    def test_missing_basic_pdf_support_message_points_to_minimal_requirements(self):
        with mock.patch.dict("sys.modules", {"pypdf": None}):
            with self.assertRaisesRegex(
                self.convert_source.ConversionError,
                "Basic PDF support is not installed",
            ):
                self.convert_source.get_pdf_reader()

    def test_doctor_reports_layered_capabilities(self):
        output = io.StringIO()

        def fake_which(name: str):
            return None

        with mock.patch.object(self.doctor.shutil, "which", side_effect=fake_which):
            with mock.patch.object(
                self.doctor,
                "has_python_module",
                side_effect=lambda name: False,
            ):
                with contextlib.redirect_stdout(output):
                    self.doctor.main()

        rendered = output.getvalue()
        self.assertIn("markitdown", rendered)
        self.assertIn(
            "Default rich-document ingestion: install `pip install -r requirements-markitdown.txt`",
            rendered,
        )
        self.assertIn(
            "Enhanced OCR PDF support: pip install -r requirements-optional.txt",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
