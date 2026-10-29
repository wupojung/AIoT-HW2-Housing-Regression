"""Dependency-free smoke checks for the published RegScope Case Package envelope.

These checks are intentionally not a full evidence/rights/production HTTP audit.
Run: python -m unittest tests.docs.test_case_package_contract -v
"""
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "web" / "data"
HEX = re.compile(r"^[0-9a-f]{64}$")
PHASES = {"phase1", "phase2", "phase3", "phase4", "phase5", "phase6"}
REQUIRED = {
    "package_schema_version", "package_id", "case_id", "package_revision",
    "package_status", "publication", "case_ref", "phases",
    "asset_manifest_ref", "files",
}


def read_bytes(path):
    return path.read_bytes()


def valid_ref(ref):
    """Lexical check only; full verifier also needs file containment/symlink checks."""
    if not isinstance(ref, str) or not ref or "\\" in ref or ":" in ref:
        return False
    if ref.startswith("/") or ref.endswith("/"):
        return False
    parts = ref.split("/")
    return all(part not in ("", ".", "..") for part in parts)


def checked_manifest_paths(entries):
    """Reject invalid and duplicate manifest paths; lexical-only smoke guard."""
    seen = set()
    for entry in entries:
        path = entry["path"]
        if not valid_ref(path):
            raise ValueError(f"invalid manifest path: {path!r}")
        if path in seen:
            raise ValueError(f"duplicate manifest path: {path!r}")
        seen.add(path)
    return seen


class ReferencePathTests(unittest.TestCase):
    def test_valid_relative_paths(self):
        for ref in ("case.json", "phases/phase-05/evaluations.json", "a-b/c_d.json"):
            with self.subTest(ref=ref):
                self.assertTrue(valid_ref(ref))

    def test_unsafe_path_lexemes(self):
        for ref in ("../a", "a/../b", "./a", "a/./b", "a//b",
                    "/a", "a/", "a\\\\b", "C:/a", "C:\\\\a",
                    "https://host/a", "file:///a", "", ".", ".."):
            with self.subTest(ref=ref):
                self.assertFalse(valid_ref(ref))

    def test_duplicate_manifest_paths_rejected(self):
        duplicate_manifest = [{"path": "case.json"}, {"path": "case.json"}]
        with self.assertRaisesRegex(ValueError, "duplicate manifest path"):
            checked_manifest_paths(duplicate_manifest)
        self.assertEqual(checked_manifest_paths([{"path": "case.json"}]), {"case.json"})


class PublishedCasePackageContractTests(unittest.TestCase):
    def test_release_index_points_to_manifest_consistent_cases(self):
        index = json.loads((DATA / "current-release.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], "1.0.0")
        self.assertTrue(index["cases"])
        ids = [case["case_id"] for case in index["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        for entry in index["cases"]:
            with self.subTest(case_id=entry["case_id"]):
                self.assertTrue(valid_ref(entry["package_ref"]))
                raw = read_bytes(DATA / entry["package_ref"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["package_sha256"])
                self.assertEqual(len(raw), entry["package_bytes"])
                pkg = json.loads(raw)
                self.assertTrue(REQUIRED.issubset(pkg))
                self.assertEqual(pkg["package_schema_version"], "1.0.0")
                self.assertEqual(pkg["case_id"], entry["case_id"])
                self.assertEqual(pkg["package_status"], entry["package_status"])
                self.assertEqual(set(pkg["phases"]), PHASES)
                self.assertIsInstance(pkg["publication"]["approved"], bool)
                self.assertIn("review_status", pkg["publication"])
                root = (DATA / entry["package_ref"]).parent
                checked_manifest_paths(pkg["files"])
                file_map = {}
                for f in pkg["files"]:
                    self.assertRegex(f["sha256"], HEX)
                    self.assertIsInstance(f["bytes"], int)
                    self.assertGreaterEqual(f["bytes"], 0)
                    self.assertIsInstance(f["mime"], str)
                    self.assertTrue(f["mime"])
                    file_map[f["path"]] = f
                refs = [pkg["case_ref"], pkg["asset_manifest_ref"]]
                refs += [p["data_ref"] for p in pkg["phases"].values()]
                for ref in refs:
                    self.assertTrue(valid_ref(ref))
                    self.assertIn(ref, file_map)
                # Only verify small, guaranteed listed control files here.
                # Full asset byte/digest validation belongs to the package verifier.
                for ref in refs:
                    raw_doc = read_bytes(root / ref)
                    self.assertEqual(len(raw_doc), file_map[ref]["bytes"])
                    self.assertEqual(hashlib.sha256(raw_doc).hexdigest(), file_map[ref]["sha256"])

    def test_cli_template_is_explicitly_not_publishable(self):
        template = ROOT / "docs/contracts/templates/package.template.json"
        pkg = json.loads(template.read_text(encoding="utf-8"))
        self.assertEqual(pkg["package_schema_version"], "1.0.0")
        self.assertFalse(pkg["publication"]["approved"])
        self.assertEqual(pkg["publication"]["review_status"], "PENDING")
        self.assertEqual(pkg["files"], [])
        self.assertEqual(set(pkg["phases"]), PHASES)


if __name__ == "__main__":
    unittest.main()
