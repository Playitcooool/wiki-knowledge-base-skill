import contextlib
import importlib.util
import io
import sys
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
            with mock.patch.object(self.doctor, "has_python_module", return_value=False):
                with contextlib.redirect_stdout(output):
                    self.doctor.main()

        rendered = output.getvalue()
        self.assertIn("Base support: md/txt ingestion + basic PDF fallback", rendered)
        self.assertIn("On-demand DOCX support: install pandoc", rendered)
        self.assertIn(
            "Enhanced OCR PDF support: pip install -r requirements-optional.txt",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
