import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
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
        analyses_path = self.phase2_dir / "phases" / "phase-02" / "analyses.json"
        self.assertTrue(analyses_path.is_file())
        decisions = output["analyses"][0]["finding"]
        self.assertIn("Id [identifier] exclude", decisions)
        self.assertIn("SalePrice [target] exclude", decisions)
        self.assertIn("LotArea [continuous] include", decisions)
        self.assertIn("Neighborhood [nominal] include", decisions)
        self.assertIn("MysteryColumn [unknown] exclude", decisions)
        self.assertIn("LotArea=1/3", output["analyses"][1]["finding"])
        self.assertIsNotNone(output["analyses"][1]["image_ref"])
        target_analysis = output["analyses"][2]
        self.assertEqual(target_analysis["status"], "MOCK")
        self.assertIsNotNone(target_analysis["image_ref"])
        self.assertIn("LotArea: n=2, min=1000, median=1500, max=2000", output["analyses"][3]["finding"])
        self.assertIn("Neighborhood: 1 distinct", output["analyses"][3]["finding"])

        refs = [analysis["image_ref"] for analysis in output["analyses"] if analysis["image_ref"]]
        self.assertGreaterEqual(len(refs), 2)
        chart_paths = []
        for ref in refs:
            ref_path = Path(ref)
            self.assertFalse(ref_path.is_absolute())
            self.assertNotIn("..", ref_path.parts)
            chart_path = self.phase2_dir / ref_path
            self.assertTrue(chart_path.is_file())
            chart_paths.append(chart_path)
            svg = chart_path.read_text(encoding="utf-8")
            ET.fromstring(svg)
            self.assertIn("<title", svg)
            self.assertIn("<desc", svg)
            self.assertIn("MOCK | SYNTHETIC DATA", svg)

        serialized = analyses_path.read_text(encoding="utf-8")
        outputs = [serialized] + [path.read_text(encoding="utf-8") for path in chart_paths]
        for private_value in (
            "9012301", "9012302", "9012303", "DO_NOT_EXPORT_ROW", "CollgCr",
            "150000", "180000", "200000", str(self.csv_path), "/Users/", "local/",
        ):
            with self.subTest(private_value=private_value):
                self.assertTrue(all(private_value not in output_text for output_text in outputs))

        before = {path: path.read_bytes() for path in [analyses_path] + chart_paths}
        with self.assertRaisesRegex(PhaseCoreError, "overwrite"):
            build_phase2(self.config, self.phase2_dir)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

        repeat_case_dir = self.root / "repeat-case"
        repeat_case_dir.mkdir()
        repeat_config = initialize_case(
            self.csv_path, "synthetic-housing", "SalePrice", repeat_case_dir
        ).config_path
        repeat_root = self.root / "phase2-repeat"
        repeat_root.mkdir()
        build_phase2(repeat_config, repeat_root)
        repeat_paths = [repeat_root / "phases" / "phase-02" / "analyses.json"] + [
            repeat_root / ref for ref in refs
        ]
        for original_path, repeat_path in zip([analyses_path] + chart_paths, repeat_paths):
            self.assertEqual(original_path.read_bytes(), repeat_path.read_bytes())

    def test_phase2_rejects_unknown_data_mode_without_writing(self):
        output_root = self.root / "invalid-mode-output"
        output_root.mkdir()
        with self.assertRaisesRegex(PhaseCoreError, "data_mode"):
            build_phase2(self.config, output_root, data_mode="verified")
        self.assertFalse((output_root / "phases").exists())

    def test_phase2_formal_missing_tokens_preserve_none_category(self):
        source = self.root / "missing-token-cases.csv"
        source.write_text(
            "Id,MasVnrType,SalePrice,YearBuilt,YearRemodAdd,GarageYrBlt,LotShape,LandSlope\n"
            '1,None,100,2000,2001,1999,Reg,Gtl\n'
            '2,NA,200,2000,2001,1999,IR1,Mod\n'
            '3,,300,2000,2001,1999,IR2,Sev\n'
            '4,N/A,400,2000,2001,1999,IR3,Gtl\n'
            '5,none,500,2000,2001,1999,Reg,Gtl\n'
            '6,null,600,2000,2001,1999,Reg,Gtl\n'
            '7,nan,700,2000,2001,1999,Reg,Gtl\n'
            '8,na,800,2000,2001,1999,Reg,Gtl\n',
            encoding="utf-8",
        )
        case_dir = self.root / "missing-token-case"
        case_dir.mkdir()
        config = initialize_case(source, "missing-token-case", "SalePrice", case_dir).config_path
        output_root = self.root / "missing-token-output"
        output_root.mkdir()

        output = build_phase2(config, output_root, data_mode="formal_development")

        self.assertEqual(output["status"], "VERIFIED")
        findings = {item["id"]: item["finding"] for item in output["analyses"]}
        self.assertIn("MasVnrType=2/8", findings["missingness"])
        self.assertIn("MasVnrType: 6 distinct", findings["feature-summary"])
        self.assertIn("YearBuilt [discrete] include", findings["field-decisions"])
        self.assertIn("YearRemodAdd [discrete] include", findings["field-decisions"])
        self.assertIn("GarageYrBlt [discrete] include", findings["field-decisions"])
        # Phase 2 and Phase 3 documents disagree on these semantic categories;
        # retain the currently implemented Phase 2 labels pending owner decision.
        self.assertIn("LotShape [ordinal] include", findings["field-decisions"])
        self.assertIn("LandSlope [ordinal] include", findings["field-decisions"])

        figures = output_root / "phases/phase-02/figures"
        missing_svg = (figures / "missingness.svg").read_text(encoding="utf-8")
        self.assertIn("MasVnrType", missing_svg)
        self.assertIn("25.0%", missing_svg)
        self.assertNotIn(">SalePrice</text>", missing_svg)
        self.assertNotIn(">YearBuilt</text>", missing_svg)
        validate_document(output, phase_schema_path(2))

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
        self.assertFalse((malformed_output_dir / "phases" / "phase-02" / "analyses.json").exists())

    def test_target_chart_is_unavailable_for_constant_or_invalid_values(self):
        cases = (
            (
                "constant",
                "Id,LotArea,Neighborhood,SalePrice\n1,1000,A,120000\n2,1100,B,120000\n",
                "constant",
            ),
            (
                "invalid",
                "Id,LotArea,Neighborhood,SalePrice\n1,1000,A,high\n2,1100,B,unknown\n",
                "non-numeric",
            ),
        )
        for case_id, csv_content, expected_reason in cases:
            with self.subTest(case_id=case_id):
                csv_path = self.root / f"{case_id}.csv"
                csv_path.write_text(csv_content, encoding="utf-8")
                config_dir = self.root / f"{case_id}-case"
                config_dir.mkdir()
                config = initialize_case(csv_path, case_id, "SalePrice", config_dir).config_path
                output_root = self.root / f"{case_id}-output"
                output_root.mkdir()

                output = build_phase2(config, output_root)
                target_view = output["analyses"][2]
                self.assertEqual(target_view["status"], "UNAVAILABLE")
                self.assertIsNone(target_view["image_ref"])
                self.assertIn(expected_reason, target_view["finding"])
                self.assertFalse(
                    (output_root / "phases" / "phase-02" / "figures" / "target-distribution.svg").exists()
                )

    def test_schema_validator_reports_invalid_documents(self):
        output = build_phase1(self.config, self.phase1_dir)
        invalid = dict(output, extra_field="not in the frozen contract")
        with self.assertRaises(ContractValidationError):
            validate_document(invalid, phase_schema_path(1))


if __name__ == "__main__":
    unittest.main()
