import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.security_scan import (
    GitScanError,
    _run_git,
    _staged_content,
    batch_staged_blobs,
    content_findings,
    is_forbidden_path,
    scan,
    scan_build_dir,
)


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

    def test_batch_staged_blobs_and_staged_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "hello.txt").write_bytes(b"hello world")
            (repo / "empty.txt").write_bytes(b"")
            subprocess.run(["git", "add", "hello.txt", "empty.txt"], cwd=repo, check=True, capture_output=True)

            blobs = batch_staged_blobs(["hello.txt", "empty.txt", "missing.txt"], cwd=repo)
            self.assertEqual(blobs.get("hello.txt"), b"hello world")
            self.assertEqual(blobs.get("empty.txt"), b"")
            self.assertIsNone(blobs.get("missing.txt"))

            single = _staged_content("hello.txt", cwd=repo)
            self.assertEqual(single, b"hello world")

    def test_batch_staged_blobs_empty_and_newline_validation(self):
        self.assertEqual(batch_staged_blobs([]), {})
        with self.assertRaises(GitScanError):
            batch_staged_blobs(["file\nwith_newline.txt"])

    def test_run_git_fails_closed_on_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(GitScanError):
                _run_git("not-a-valid-git-command", cwd=Path(temp_dir))

    def test_run_git_fails_closed_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["git", "status"], timeout=0.1)):
            with self.assertRaises(GitScanError) as ctx:
                _run_git("status")
            self.assertIn("timed out", str(ctx.exception))

    def test_batch_staged_blobs_fails_closed_on_timeout(self):
        mock_proc = unittest.mock.MagicMock()
        mock_proc.communicate.side_effect = [subprocess.TimeoutExpired(cmd=["git"], timeout=0.1), (b"", b"")]
        mock_proc.__enter__.return_value = mock_proc
        with patch("subprocess.Popen", return_value=mock_proc):
            with self.assertRaises(GitScanError) as ctx:
                batch_staged_blobs(["sample.txt"])
            self.assertIn("timed out", str(ctx.exception))

    def test_batch_staged_blobs_fails_closed_on_truncated_output(self):
        fake_stdout = b"0000000000000000000000000000000000000000 blob 20\ntruncated\n"
        mock_proc = unittest.mock.MagicMock()
        mock_proc.communicate.return_value = (fake_stdout, b"")
        mock_proc.returncode = 0
        mock_proc.__enter__.return_value = mock_proc
        with patch("subprocess.Popen", return_value=mock_proc):
            with self.assertRaises(GitScanError) as ctx:
                batch_staged_blobs(["sample.txt"])
            self.assertIn("Truncated blob", str(ctx.exception))

    def test_scan_staged_detects_synthetic_secret(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            secret_file = repo / "test_api.py"
            secret_file.write_bytes(b"api" + b"_key = 'synthetic-secret-token-123456'")
            subprocess.run(["git", "add", "test_api.py"], cwd=repo, check=True, capture_output=True)

            findings = scan("staged", root=repo)
            self.assertTrue(any("possible generic credential assignment" in f for f in findings))

    def test_scan_staged_fails_closed_on_metadata_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Not a git repo -> git diff and git ls-files fail closed
            non_repo = Path(temp_dir)
            findings = scan("staged", root=non_repo)
            self.assertTrue(any("Git metadata scan error" in f for f in findings))

    def test_scan_staged_fails_closed_on_blob_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            (repo / "file.txt").write_bytes(b"sample")
            subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True, capture_output=True)

            with patch("tools.security_scan.batch_staged_blobs", side_effect=GitScanError("cat-file failure")):
                findings = scan("staged", root=repo)
            self.assertTrue(any("Git blob scan error" in f for f in findings))

    def test_ci_security_workflow_gates_main_and_deploy(self):
        workflow_path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "security.yml"
        self.assertTrue(workflow_path.is_file(), "security.yml must exist")
        import yaml
        workflow_data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        trigger_section = workflow_data.get("on") or workflow_data.get(True, {})
        pr_branches = trigger_section.get("pull_request", {}).get("branches", [])
        self.assertIn("main", pr_branches)
        self.assertIn("deploy", pr_branches)

    def test_pre_commit_config_disables_automatic_local_scanner(self):
        config_path = Path(__file__).resolve().parents[2] / ".pre-commit-config.yaml"
        self.assertTrue(config_path.is_file(), ".pre-commit-config.yaml must exist")
        import yaml
        config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        hooks = [hook for repo in config_data.get("repos", []) for hook in repo.get("hooks", [])]
        self.assertFalse(any("security_scan" in hook.get("entry", "") for hook in hooks))


if __name__ == "__main__":
    unittest.main()
