import unittest
import tempfile
from pathlib import Path

from tools.security_scan import content_findings, is_forbidden_path, scan_build_dir


class SecurityScanTests(unittest.TestCase):
    def test_blocks_local_and_sensitive_artifact_paths(self):
        for path in (
            "local/research/metadata.json",
            "papers/article.pdf",
            "data/housing.csv",
            ".env",
            "credentials.json",
            "service-account-prod.json",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_forbidden_path(path))

    def test_allows_safe_public_project_files(self):
        for path in ("README.md", "tools/research_collector/sources.yaml", ".env.example"):
            with self.subTest(path=path):
                self.assertFalse(is_forbidden_path(path))

    def test_vercelignore_excludes_local_and_sensitive_file_classes(self):
        ignore_file = Path(__file__).resolve().parents[2] / ".vercelignore"
        patterns = set(ignore_file.read_text(encoding="utf-8").splitlines())
        for pattern in ("local/", ".env", "*.pdf", "*.csv", "credentials.json", "service-account*.json"):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, patterns)

    def test_detects_synthetic_secret_patterns(self):
        synthetic_samples = (
            b"-----BEGIN " + b"PRIVATE KEY-----\nfake\n",
            b"api" + b"_key = '" + b"synthetic-test-value-123456'",
            b"ghp_" + b"abcdefghijklmnopqrstuvwxyz0123456789",
        )
        for sample in synthetic_samples:
            with self.subTest(sample=sample[:12]):
                self.assertTrue(content_findings(sample))

    def test_does_not_flag_placeholder_or_variable_name(self):
        self.assertEqual(content_findings(b"API" + b"_KEY=\nRESEARCH_OUTPUT_DIR=local/research\n"), [])

    def test_build_scan_detects_synthetic_sensitive_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "assets" / "bundle.js"
            artifact.parent.mkdir()
            artifact.write_bytes(b"client_secret='" + b"synthetic-build-secret-123456'")
            self.assertTrue(scan_build_dir(Path(temp_dir)))

    def test_build_scan_blocks_local_pdf_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "local" / "papers" / "synthetic-paper.pdf"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"synthetic placeholder")
            self.assertTrue(scan_build_dir(Path(temp_dir)))


if __name__ == "__main__":
    unittest.main()
