import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python" / "src"))

from housing_regression.contracts import ContractValidationError, phase_schema_path, validate_document
from housing_regression.init_config import initialize_case
from housing_regression.phase1_core import PhaseCoreError, build_phase1
from housing_regression.phase2_core import build_phase2


FIXTURES = ROOT / "tests" / "fixtures"


class Phase12CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.case_dir = self.root / "case"
        self.case_dir.mkdir()
        self.phase1_dir = self.root / "phase1"
        self.phase1_dir.mkdir()
        self.phase2_dir = self.root / "phase2"
        self.phase2_dir.mkdir()
        self.csv_path = FIXTURES / "regscope_g2_synthetic.csv.fixture"
        self.config = initialize_case(
            self.csv_path, "synthetic-housing", "SalePrice", self.case_dir
        ).config_path

    def tearDown(self):
        self.temp.cleanup()

    def test_phase1_unavailable_is_empty_and_schema_valid(self):
        output = build_phase1(self.config, self.phase1_dir)

        self.assertEqual(output["status"], "UNAVAILABLE")
        self.assertEqual(output["sections"], [])
        self.assertTrue((self.phase1_dir / "content.json").is_file())
        validate_document(output, phase_schema_path(1))

    def test_phase1_only_uses_complete_explicit_evidence(self):
        output_dir = self.root / "phase1-evidence"
        output_dir.mkdir()
        output = build_phase1(
            self.config,
            output_dir,
            {
                "business_question": "Describe a synthetic housing example.",
                "source_description": "Synthetic fixture created for tests.",
                "license_or_rights": "Synthetic fixture; no external rights claim.",
            },
        )
        self.assertEqual(output["status"], "MOCK")
        self.assertEqual(len(output["sections"]), 3)
        validate_document(output, phase_schema_path(1))

        partial_dir = self.root / "phase1-partial"
        partial_dir.mkdir()
        partial = build_phase1(
            self.config, partial_dir, {"business_question": "One explicit item only."}
        )
        self.assertEqual(partial["status"], "UNAVAILABLE")
        self.assertEqual(partial["sections"], [])
        validate_document(partial, phase_schema_path(1))

    def test_phase1_path_guard_allows_https_and_rejects_local_paths(self):
        https_dir = self.root / "phase1-public-https"
        https_dir.mkdir()
        public = build_phase1(
            self.config,
            https_dir,
            {
                "business_question": "Describe a synthetic example.",
                "source_description": "Public source reference: https://example.org/data.csv; ratio 1/2.",
                "license_or_rights": "Synthetic fixture; no external rights claim.",
            },
        )
        self.assertEqual(public["status"], "MOCK")
        self.assertIn("https://example.org/data.csv", public["sections"][1]["body"])
        validate_document(public, phase_schema_path(1))
        original = (https_dir / "content.json").read_bytes()
        with self.assertRaisesRegex(PhaseCoreError, "overwrite"):
            build_phase1(
                self.config,
                https_dir,
                {
                    "business_question": "Describe a synthetic example.",
                    "source_description": "https://example.org/data.csv",
                    "license_or_rights": "Synthetic fixture.",
                },
            )
        self.assertEqual((https_dir / "content.json").read_bytes(), original)

        private_paths = (
            "/tmp/data.csv",
            "~/data.csv",
            "~alice/data.csv",
            r"C:\Users\x\data.csv",
            r"\\server\share\data.csv",
            "file:///private.csv",
            "../local/data.csv",
        )
        for index, source_reference in enumerate(private_paths):
            with self.subTest(source_reference=source_reference):
                output_dir = self.root / f"phase1-private-{index}"
                output_dir.mkdir()
                with self.assertRaisesRegex(PhaseCoreError, "private path"):
                    build_phase1(
                        self.config,
                        output_dir,
                        {
                            "business_question": "Describe a synthetic example.",
                            "source_description": f"Source reference: {source_reference}",
                            "license_or_rights": "Synthetic fixture.",
                        },
                    )
                self.assertFalse((output_dir / "content.json").exists())

    def test_phase2_profiles_aggregates_and_excludes_ids_target_and_unknowns(self):
        output = build_phase2(self.config, self.phase2_dir)
        validate_document(output, phase_schema_path(2))

        self.assertEqual(output["status"], "MOCK")
        self.assertEqual(output["default_analysis_id"], "field-decisions")
        self.assertTrue((self.phase2_dir / "analyses.json").is_file())
        decisions = output["analyses"][0]["finding"]
        self.assertIn("Id [identifier] exclude", decisions)
        self.assertIn("SalePrice [target] exclude", decisions)
        self.assertIn("LotArea [continuous] include", decisions)
        self.assertIn("Neighborhood [nominal] include", decisions)
        self.assertIn("MysteryColumn [unknown] exclude", decisions)
        self.assertIn("LotArea=1/3", output["analyses"][1]["finding"])
        self.assertIn("LotArea: n=2, min=1000, median=1500, max=2000", output["analyses"][2]["finding"])
        self.assertIn("Neighborhood: 1 distinct", output["analyses"][2]["finding"])

        serialized = (self.phase2_dir / "analyses.json").read_text(encoding="utf-8")
        for private_value in (
            "9012301", "9012302", "9012303", "DO_NOT_EXPORT_ROW", "CollgCr",
            str(self.csv_path), "/Users/", "local/",
        ):
            with self.subTest(private_value=private_value):
                self.assertNotIn(private_value, serialized)

    def test_empty_phase2_is_unavailable_and_invalid_csv_fails_without_output(self):
        empty_dir = self.root / "empty-case"
        empty_dir.mkdir()
        empty_config = initialize_case(
            FIXTURES / "regscope_g2_empty.csv.fixture", "empty-housing", "SalePrice", empty_dir
        ).config_path
        empty_output_dir = self.root / "empty-output"
        empty_output_dir.mkdir()
        empty_output = build_phase2(empty_config, empty_output_dir)
        self.assertEqual(empty_output["status"], "UNAVAILABLE")
        self.assertEqual(empty_output["analyses"], [])
        self.assertIsNone(empty_output["default_analysis_id"])
        validate_document(empty_output, phase_schema_path(2))

        malformed_dir = self.root / "malformed-case"
        malformed_dir.mkdir()
        malformed_config = initialize_case(
            FIXTURES / "regscope_g2_malformed.csv.fixture", "malformed-housing", "SalePrice", malformed_dir
        ).config_path
        malformed_output_dir = self.root / "malformed-output"
        malformed_output_dir.mkdir()
        with self.assertRaisesRegex(PhaseCoreError, "invalid column count"):
            build_phase2(malformed_config, malformed_output_dir)
        self.assertFalse((malformed_output_dir / "analyses.json").exists())

    def test_schema_validator_reports_invalid_documents(self):
        output = build_phase1(self.config, self.phase1_dir)
        invalid = dict(output, extra_field="not in the frozen contract")
        with self.assertRaises(ContractValidationError):
            validate_document(invalid, phase_schema_path(1))


if __name__ == "__main__":
    unittest.main()
