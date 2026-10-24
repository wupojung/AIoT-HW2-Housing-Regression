import json
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from tools.eda.full_ames_eda import (
    EXPECTED,
    ALIAS_MAP,
    parse_data_description,
    crosswalk_dictionary,
    calculate_numeric_stats,
    run,
)


class FullAmesEdaTests(unittest.TestCase):
    def test_blocks_without_owner_terms_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "Confirm Kaggle"):
                run(root, root / "out", "2026-10-24", False)

    def test_missing_files_are_reported_without_eda(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            data = local / "datasets"
            data.mkdir(parents=True)
            for name in EXPECTED - {"train.csv"}:
                (data / name).write_text("Id,foo\n1,x\n")
            with self.assertRaisesRegex(FileNotFoundError, "train.csv"):
                run(data, local / "research", "2026-10-24", True, local_root=local)
            self.assertFalse((local / "research").exists())

    def test_rejects_output_outside_local(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            data = local / "datasets"
            data.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "inside ignored local"):
                run(data, Path(temp) / "public", "2026-10-24", True, local_root=local)

    def test_rejects_output_inside_dataset_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            data = local / "datasets"
            data.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "outside local/datasets"):
                run(data, data / "profile", "2026-10-24", True, local_root=local)

    def test_rejects_symlinked_dataset_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            local.mkdir()
            data = local / "datasets"
            data.mkdir()
            actual = Path.is_symlink

            def simulated_symlink(path):
                return path.absolute() == data.absolute() or actual(path)

            with patch.object(Path, "is_symlink", simulated_symlink):
                with self.assertRaisesRegex(ValueError, "must not be a symlink"):
                    run(data, local / "research", "2026-10-24", True, local_root=local)

    def test_rejects_symlinked_input_file(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            data = local / "datasets"
            data.mkdir(parents=True)
            (data / "train.csv").write_text("Id,SalePrice\n1,100\n")
            (data / "data_description.txt").write_text("SalePrice: Target\n")
            (data / "sample_submission.csv").write_text("Id,SalePrice\n2,100\n")
            test_csv = data / "test.csv"
            test_csv.write_text("Id\n2\n")
            actual = Path.is_symlink

            def simulated_symlink(path):
                return path.absolute() == test_csv.absolute() or actual(path)

            with patch.object(Path, "is_symlink", simulated_symlink):
                with self.assertRaisesRegex(ValueError, "must not be symlinks"):
                    run(data, local / "research", "2026-10-24", True, local_root=local)

    def test_data_description_parsing_and_aliases(self):
        with tempfile.TemporaryDirectory() as temp:
            txt_path = Path(temp) / "data_description.txt"
            txt_path.write_text(
                "MSSubClass: Identifies dwelling type\n"
                "       20\t1-Story 1946 & Newer\n"
                "       30\t1-Story 1945 & Older\n\n"
                "1stFlrSF: First Floor square feet\n\n"
                "Bedroom: Bedrooms above grade\n\n"
                "Kitchen: Kitchens above grade\n"
            )
            headings = parse_data_description(txt_path)
            self.assertIn("MSSubClass", headings)
            self.assertIn("1stFlrSF", headings)
            self.assertIn("Bedroom", headings)
            self.assertIn("Kitchen", headings)
            self.assertEqual(len(headings["MSSubClass"]["levels"]), 2)

            train_cols = {"Id", "SalePrice", "MSSubClass", "1stFlrSF", "BedroomAbvGr", "KitchenAbvGr"}
            test_cols = {"Id", "MSSubClass", "1stFlrSF", "BedroomAbvGr", "KitchenAbvGr"}
            cross = crosswalk_dictionary(train_cols, test_cols, headings)
            self.assertEqual(cross["field_status"]["BedroomAbvGr"], "definition_alias")
            self.assertEqual(cross["field_status"]["KitchenAbvGr"], "definition_alias")
            self.assertEqual(cross["field_status"]["1stFlrSF"], "definition_present")
            self.assertEqual(cross["field_status"]["SalePrice"], "target")
            self.assertEqual(cross["field_status"]["Id"], "identifier")
            self.assertEqual(len(cross["unmapped_dictionary_headings"]), 0)

    def test_numeric_stats_and_iqr(self):
        data = [10.0, 12.0, 14.0, 15.0, 16.0, 18.0, 20.0, 100.0]
        stats = calculate_numeric_stats(data)
        self.assertEqual(stats["count"], 8)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 100.0)
        self.assertGreater(stats["anomaly_candidates_count"], 0)
        self.assertGreater(stats["skewness"], 1.0)

    def test_full_synthetic_pipeline_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            # 1. train.csv (4 records)
            train_content = (
                "Id,MSSubClass,1stFlrSF,BedroomAbvGr,Alley,SalePrice\n"
                "1,20,1000,3,,150000\n"
                "2,20,1200,3,Grvl,180000\n"
                "3,60,1500,4,,220000\n"
                "4,120,800,2,,130000\n"
            )
            (datasets / "train.csv").write_text(train_content)

            # 2. test.csv (2 records)
            test_content = (
                "Id,MSSubClass,1stFlrSF,BedroomAbvGr,Alley\n"
                "5,20,1100,3,\n"
                "6,60,1400,4,Pave\n"
            )
            (datasets / "test.csv").write_text(test_content)

            # 3. sample_submission.csv
            sample_content = (
                "Id,SalePrice\n"
                "5,160000\n"
                "6,200000\n"
            )
            (datasets / "sample_submission.csv").write_text(sample_content)

            # 4. data_description.txt
            desc_content = (
                "MSSubClass: Identifies dwelling type\n"
                "       20\t1-Story 1946 & Newer\n"
                "       60\t2-Story 1946 & Newer\n\n"
                "1stFlrSF: First floor square feet\n\n"
                "Bedroom: Bedrooms above grade\n\n"
                "Alley: Type of alley access\n"
                "       Grvl\tGravel\n"
                "       Pave\tPaved\n"
                "       NA \tNo alley access\n"
            )
            (datasets / "data_description.txt").write_text(desc_content)

            # Run EDA
            report = run(datasets, output, "2026-10-24", True, local_root=local)

            self.assertEqual(report["status"], "descriptive_profile_generated_pending_review")
            self.assertEqual(len(report["input_files"]), 4)
            for fname, finfo in report["input_files"].items():
                self.assertEqual(len(finfo["sha256"]), 64)

            self.assertTrue(report["schema_checks"]["training_target_present"])
            self.assertTrue(report["schema_checks"]["test_target_absent"])
            self.assertTrue(report["schema_checks"]["train_id_unique"])
            self.assertTrue(report["schema_checks"]["test_id_unique"])
            self.assertEqual(report["schema_checks"]["train_test_id_overlap_count"], 0)
            self.assertTrue(report["schema_checks"]["test_ids_match_sample_submission"])

            # Verify files on disk
            self.assertTrue((output / "profile.json").exists())
            self.assertTrue((output / "field_manifest.json").exists())
            self.assertTrue((output / "field_manifest.csv").exists())
            self.assertTrue((output / "figures_manifest.json").exists())
            self.assertTrue((output / "figures_manifest.csv").exists())
            figures = __import__("json").loads((output / "figures_manifest.json").read_text())
            self.assertFalse(any(item["figure_id"] == "FIG-NUM-Id" for item in figures))
            self.assertTrue((output / "correlation_matrix.csv").exists())
            self.assertTrue((output / "report.md").exists())

            # Verify figures directory and assets
            self.assertTrue((output / "figures").is_dir())
            self.assertTrue((output / "figures/fig01_dataset_overview.svg").exists())
            self.assertTrue((output / "figures/fig02_missingness_overview.svg").exists())
            self.assertTrue((output / "figures/fig03_saleprice_distribution.svg").exists())
            self.assertTrue((output / "figures/fig06_numeric_correlation_heatmap.svg").exists())

            # Verify no zero-byte PNGs
            png_files = list((output / "figures").glob("*.png"))
            self.assertGreater(len(png_files), 0)
            for png in png_files:
                content = png.read_bytes()
                self.assertGreater(len(content), 0, f"PNG {png.name} must not be zero bytes")
                self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"), f"PNG {png.name} must have valid PNG signature")

            # Verify report does not contain unsupported hard-coded claims
            report_text = (output / "report.md").read_text(encoding="utf-8")
            self.assertNotIn("Train: 1 ~ 1,460", report_text)
            self.assertNotIn("80 個預測變數", report_text)
            self.assertNotIn("地下室相關特徵 (`BsmtQual`", report_text)
            self.assertNotIn("車庫相關特徵 (`GarageType`", report_text)

            # Verify per-split distributions in field manifest
            import json
            fields = json.loads((output / "field_manifest.json").read_text(encoding="utf-8"))
            mssubclass = next(f for f in fields if f["name"] == "MSSubClass")
            self.assertIsNotNone(mssubclass["train_numeric_stats"])
            self.assertIsNotNone(mssubclass["test_numeric_stats"])
            alley = next(f for f in fields if f["name"] == "Alley")
            self.assertIsNotNone(alley["train_categorical_distribution"])
            self.assertIsNotNone(alley["test_categorical_distribution"])

    def test_schema_checks_fail_truthfully_in_report(self):
        """Verify report dynamically derives PASS/FAIL from schema_checks without hardcoding PASS."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            # Train has ID 1, 2; Test has ID 2, 3 (ID overlap!)
            # Predictor count is only 2 (MSSubClass, Alley) -> < 14
            # test.csv has an extra column 'ExtraCol' not in train
            (datasets / "train.csv").write_text(
                "Id,MSSubClass,Alley,SalePrice\n"
                "1,20,Grvl,100000\n"
                "2,60,,200000\n"
            )
            (datasets / "test.csv").write_text(
                "Id,MSSubClass,Alley,ExtraCol\n"
                "2,20,Pave,A\n"
                "3,60,,B\n"
            )
            (datasets / "sample_submission.csv").write_text(
                "Id,SalePrice\n"
                "2,100000\n"
                "3,200000\n"
            )
            (datasets / "data_description.txt").write_text(
                "MSSubClass: Type\nAlley: Type\nExtraCol: Extra\n"
            )

            report = run(datasets, output, "2026-10-24", True, local_root=local)

            self.assertFalse(report["schema_checks"]["original_predictor_count_at_least_14"])
            self.assertEqual(report["schema_checks"]["train_test_id_overlap_count"], 1)

            report_text = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("| **原創特徵數量檢核** | **FAIL** |", report_text)
            self.assertIn("| **Train / Test ID 重疊檢驗** | **FAIL** |", report_text)
            self.assertIn("| **預測欄位對等性** | **FAIL** |", report_text)

    def test_png_truthfulness_when_matplotlib_unavailable(self):
        """Verify non-zero truthful (non-uniform) PNG creation when matplotlib is unavailable."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            (datasets / "train.csv").write_text(
                "Id,MSSubClass,SalePrice\n"
                "1,20,100000\n"
                "2,60,200000\n"
            )
            (datasets / "test.csv").write_text(
                "Id,MSSubClass\n"
                "3,20\n"
                "4,60\n"
            )
            (datasets / "sample_submission.csv").write_text(
                "Id,SalePrice\n"
                "3,100000\n"
                "4,200000\n"
            )
            (datasets / "data_description.txt").write_text("MSSubClass: Type\n")

            with patch("tools.eda.full_ames_eda.HAS_MATPLOTLIB", False):
                run(datasets, output, "2026-10-24", True, local_root=local)

            png_files = list((output / "figures").glob("*.png"))
            self.assertGreater(len(png_files), 0)
            for png in png_files:
                data = png.read_bytes()
                self.assertGreater(len(data), 0, f"{png.name} must not be empty")
                self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"), f"{png.name} must be a valid PNG")

                # Decompress IDAT to confirm truthful drawing with multiple distinct colors (not single-color uniform fallback)
                idx = 8
                idat_bytes = bytearray()
                w = int.from_bytes(data[16:20], "big")
                h = int.from_bytes(data[20:24], "big")
                while idx < len(data):
                    length = int.from_bytes(data[idx : idx + 4], "big")
                    tag = data[idx + 4 : idx + 8]
                    if tag == b"IDAT":
                        idat_bytes.extend(data[idx + 8 : idx + 8 + length])
                    idx += 12 + length
                raw = zlib.decompress(bytes(idat_bytes))
                unique_colors = set()
                row_len = 1 + w * 3
                for y in range(h):
                    row = raw[y * row_len + 1 : (y + 1) * row_len]
                    for x in range(0, len(row), 3):
                        unique_colors.add(tuple(row[x : x + 3]))
                self.assertGreater(len(unique_colors), 1, f"{png.name} must contain truthful distinct colors, not uniform block")

    def test_fails_clearly_when_matplotlib_required_and_unavailable(self):
        """Verify clear failure when matplotlib is required but unavailable."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            (datasets / "train.csv").write_text("Id,MSSubClass,SalePrice\n1,20,100000\n")
            (datasets / "test.csv").write_text("Id,MSSubClass\n2,20\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n2,100000\n")
            (datasets / "data_description.txt").write_text("MSSubClass: Type\n")

            with patch("tools.eda.full_ames_eda.HAS_MATPLOTLIB", False):
                with self.assertRaisesRegex(RuntimeError, "Matplotlib is required"):
                    run(datasets, output, "2026-10-24", True, local_root=local, require_matplotlib=True)

    def test_undefined_correlations_masked_not_zero(self):
        """Verify constant columns and insufficient pairs remain undefined (None), rendered as #d0d0d0 with legend."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            # ConstantVal has 0 variance; SparseVal has only 1 observation with Target -> insufficient pairs
            (datasets / "train.csv").write_text(
                "Id,MSSubClass,ConstantVal,SparseVal,SalePrice\n"
                "1,20,50,10,100000\n"
                "2,60,50,,200000\n"
                "3,80,50,,300000\n"
            )
            (datasets / "test.csv").write_text("Id,MSSubClass,ConstantVal,SparseVal\n4,20,50,\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n4,150000\n")
            (datasets / "data_description.txt").write_text(
                "MSSubClass: Type\nConstantVal: Constant\nSparseVal: Sparse\n"
            )

            report = run(datasets, output, "2026-10-24", True, local_root=local)
            import json
            profile = json.loads((output / "profile.json").read_text(encoding="utf-8"))

            corrs = profile.get("correlations_summary", {})
            # Verify ConstantVal vs SalePrice is None (masked), not 0.0
            from tools.eda.full_ames_eda import calculate_numeric_correlations
            cols, rows = ["Id", "MSSubClass", "ConstantVal", "SparseVal", "SalePrice"], [
                {"Id": "1", "MSSubClass": "20", "ConstantVal": "50", "SparseVal": "10", "SalePrice": "100000"},
                {"Id": "2", "MSSubClass": "60", "ConstantVal": "50", "SparseVal": "", "SalePrice": "200000"},
                {"Id": "3", "MSSubClass": "80", "ConstantVal": "50", "SparseVal": "", "SalePrice": "300000"},
            ]
            full_corrs = calculate_numeric_correlations(cols, rows)
            pw = full_corrs["pairwise_correlations"]
            self.assertIsNone(pw["ConstantVal"]["SalePrice"]["r"])
            self.assertEqual(pw["ConstantVal"]["SalePrice"]["reason"], "zero_variance")
            self.assertIsNone(pw["SparseVal"]["SalePrice"]["r"])
            self.assertEqual(pw["SparseVal"]["SalePrice"]["reason"], "insufficient_pairs")

            # Check heatmap SVG contains #d0d0d0 and explicit legend
            svg_text = (output / "figures/fig06_numeric_correlation_heatmap.svg").read_text(encoding="utf-8")
            self.assertIn("#d0d0d0", svg_text)
            self.assertIn("Undefined / Masked", svg_text)

    def test_adversarial_symmetric_and_left_skewed_saleprice(self):
        """Verify captions and narrative are data-derived and truthfully report left-skewed SalePrice."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            # Synthetic left-skewed values
            (datasets / "train.csv").write_text(
                "Id,MSSubClass,SalePrice\n"
                "1,20,50000\n"
                "2,20,180000\n"
                "3,20,190000\n"
                "4,20,195000\n"
                "5,20,200000\n"
                "6,20,205000\n"
                "7,20,210000\n"
            )
            (datasets / "test.csv").write_text("Id,MSSubClass\n8,20\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n8,200000\n")
            (datasets / "data_description.txt").write_text("MSSubClass: Type\n")

            run(datasets, output, "2026-10-24", True, local_root=local)

            import json
            figs = json.loads((output / "figures_manifest.json").read_text(encoding="utf-8"))
            fig03 = next(f for f in figs if f["figure_id"] == "FIG-03")
            self.assertIn("左偏態分佈", fig03["descriptive_observation"])
            self.assertNotIn("右偏態分佈", fig03["descriptive_observation"])

            report_text = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("左偏態分佈", report_text)
            self.assertNotIn("右側尾部", report_text)

    def test_adversarial_flat_and_negative_feature_associations(self):
        """Verify FIG-07 observation truthfully reflects negative and flat associations without claiming upward trends."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            # OverallQual is negatively correlated with SalePrice; GrLivArea is flat
            (datasets / "train.csv").write_text(
                "Id,OverallQual,GrLivArea,SalePrice\n"
                "1,10,1000,50000\n"
                "2,8,1000,100000\n"
                "3,6,1000,150000\n"
                "4,4,1000,200000\n"
                "5,2,1000,250000\n"
            )
            (datasets / "test.csv").write_text("Id,OverallQual,GrLivArea\n6,5,1000\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n6,150000\n")
            (datasets / "data_description.txt").write_text("OverallQual: Qual\nGrLivArea: Area\n")

            run(datasets, output, "2026-10-24", True, local_root=local)

            import json
            figs = json.loads((output / "figures_manifest.json").read_text(encoding="utf-8"))
            fig07 = next(f for f in figs if f["figure_id"] == "FIG-07")
            self.assertIn("負向線性關聯趨勢", fig07["descriptive_observation"])
            self.assertIn("無明顯線性趨勢 (平緩或無線性關聯)", fig07["descriptive_observation"])
            self.assertIn("GrLivArea", fig07["descriptive_observation"])
            self.assertNotIn("向上趨勢", fig07["descriptive_observation"])
            self.assertNotEqual("散佈圖關聯性檢視：。", fig07["descriptive_observation"].strip())

            # Fully flat dataset verification: all selected features flat/invariant
            (datasets / "train.csv").write_text(
                "Id,OverallQual,GrLivArea,SalePrice\n"
                "1,5,1000,100000\n"
                "2,5,1000,150000\n"
                "3,5,1000,200000\n"
            )
            run(datasets, output, "2026-10-24", True, local_root=local)
            figs_flat = json.loads((output / "figures_manifest.json").read_text(encoding="utf-8"))
            fig07_flat = next(f for f in figs_flat if f["figure_id"] == "FIG-07")
            self.assertIn("無明顯線性趨勢 (平緩或無線性關聯)", fig07_flat["descriptive_observation"])
            self.assertNotIn("正向線性關聯", fig07_flat["descriptive_observation"])
            self.assertNotIn("負向線性關聯", fig07_flat["descriptive_observation"])
            self.assertNotEqual("散佈圖關聯性檢視：。", fig07_flat["descriptive_observation"].strip())

    def test_rejects_malformed_csv_rows_in_full_eda(self):
        """Verify full EDA fails closed when CSV contains malformed rows (extra or missing cells)."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            (datasets / "train.csv").write_text("Id,MSSubClass,SalePrice\n1,20,100000,EXTRA\n")
            (datasets / "test.csv").write_text("Id,MSSubClass\n2,20\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n2,100000\n")
            (datasets / "data_description.txt").write_text("MSSubClass: Type\n")

            with self.assertRaisesRegex(ValueError, "Malformed CSV.*expected 3 fields, got 4"):
                run(datasets, output, "2026-10-24", True, local_root=local)

            # Test missing cells row
            (datasets / "train.csv").write_text("Id,MSSubClass,SalePrice\n1,20\n")
            with self.assertRaisesRegex(ValueError, "Malformed CSV.*expected 3 fields, got 2"):
                run(datasets, output, "2026-10-24", True, local_root=local)

    def test_rejects_non_finite_numeric_values_in_full_eda(self):
        """Verify full EDA fails closed on non-finite numeric floats (inf, nan)."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            (datasets / "train.csv").write_text("Id,MSSubClass,SalePrice\n1,20,inf\n")
            (datasets / "test.csv").write_text("Id,MSSubClass\n2,20\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n2,100000\n")
            (datasets / "data_description.txt").write_text("MSSubClass: Type\n")

            with self.assertRaisesRegex(ValueError, "Non-finite numeric value"):
                run(datasets, output, "2026-10-24", True, local_root=local)

    def test_reports_duplicate_id_count_in_schema_checks(self):
        """Verify duplicate ID count is explicitly reported in schema_checks and report.md."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            # Train has ID 1 duplicated; Test has ID 3 duplicated
            (datasets / "train.csv").write_text(
                "Id,MSSubClass,SalePrice\n"
                "1,20,100000\n"
                "1,20,110000\n"
                "2,60,200000\n"
            )
            (datasets / "test.csv").write_text(
                "Id,MSSubClass\n"
                "3,20\n"
                "3,20\n"
            )
            (datasets / "sample_submission.csv").write_text(
                "Id,SalePrice\n"
                "3,100000\n"
                "3,100000\n"
            )
            (datasets / "data_description.txt").write_text("MSSubClass: Type\n")

            report = run(datasets, output, "2026-10-24", True, local_root=local)

            self.assertFalse(report["schema_checks"]["train_id_unique"])
            self.assertEqual(report["schema_checks"]["train_duplicate_id_count"], 1)
            self.assertFalse(report["schema_checks"]["test_id_unique"])
            self.assertEqual(report["schema_checks"]["test_duplicate_id_count"], 1)

            report_text = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("訓練集重複: 1 筆", report_text)
            self.assertIn("測試集重複: 1 筆", report_text)

    def test_single_main_entrypoint_guard(self):
        """Regression test ensuring full_ames_eda.py contains exactly one __main__ guard."""
        import tools.eda.full_ames_eda
        script_path = Path(tools.eda.full_ames_eda.__file__).resolve()
        content = script_path.read_text(encoding="utf-8")
        guard_matches = content.count('if __name__ == "__main__":')
        self.assertEqual(guard_matches, 1, "Expected exactly one '__main__' entrypoint guard in full_ames_eda.py")

    def test_main_cli_invokes_run_exactly_once(self):
        """Verify CLI main entrypoint invokes run exactly once."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            (datasets / "train.csv").write_text("Id,MSSubClass,SalePrice\n1,20,100000\n")
            (datasets / "test.csv").write_text("Id,MSSubClass\n2,20\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n2,100000\n")
            (datasets / "data_description.txt").write_text("MSSubClass: Type\n")

            from tools.eda.full_ames_eda import main
            test_args = [
                "full_ames_eda.py",
                "--data-dir", str(datasets),
                "--output-dir", str(output),
                "--access-date", "2026-10-24",
                "--terms-confirmed",
            ]
            with patch("sys.argv", test_args), patch("tools.eda.full_ames_eda.run") as mock_run, patch("builtins.print"):
                mock_run.return_value = {
                    "status": "ok",
                    "figure_count_total": 0,
                }
                main()
                self.assertEqual(mock_run.call_count, 1)

    def test_scatters_chart_with_matplotlib_filters_categorical_fallback(self):
        """Verify that when HAS_MATPLOTLIB is True and preferred features are absent,
        only truly numeric predictors are selected and categorical fallback fields (e.g. Alley)
        are never passed to float conversion or plotted as numeric predictors.
        """
        import tools.eda.full_ames_eda as eda

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            p_png = out_dir / "fig07_scatters.png"
            p_svg = out_dir / "fig07_scatters.svg"

            # Synthetic dataset: preferred features absent.
            # Contains numeric predictor MSSubClass, categorical predictor Alley, and target SalePrice.
            train_rows = [
                {"Id": "1", "MSSubClass": "20", "Alley": "Grvl", "SalePrice": "100000"},
                {"Id": "2", "MSSubClass": "60", "Alley": "", "SalePrice": "200000"},
            ]

            # 1. Verify numeric predictor selection strictly filters categorical Alley
            numeric_preds = eda._get_numeric_predictors(train_rows)
            self.assertEqual(numeric_preds, ["MSSubClass"])
            self.assertNotIn("Alley", numeric_preds)

            # 2. Verify associations summary does not mislabel Alley
            correlations = eda.calculate_numeric_correlations(["Id", "MSSubClass", "Alley", "SalePrice"], train_rows)
            obs = eda._describe_saleprice_associations(train_rows, correlations)
            self.assertNotIn("Alley", obs)
            self.assertIn("MSSubClass", obs)

            # 3. Exercise HAS_MATPLOTLIB=True path without float("Grvl") crash
            if eda.HAS_MATPLOTLIB:
                eda._render_scatters_chart(p_png, p_svg, train_rows)
                self.assertTrue(p_png.exists())
                self.assertGreater(p_png.stat().st_size, 0)
                self.assertTrue(p_svg.exists())
            else:
                from unittest.mock import MagicMock
                mock_plt = MagicMock()
                mock_fig = MagicMock()
                mock_ax = MagicMock()
                mock_plt.subplots.return_value = (mock_fig, mock_ax)

                def fake_savefig(target, *args, **kwargs):
                    Path(target).write_bytes(b"\x89PNG\r\n\x1a\nfake_png")

                mock_fig.savefig.side_effect = fake_savefig

                with patch.object(eda, "HAS_MATPLOTLIB", True), patch.object(eda, "plt", mock_plt, create=True):
                    eda._render_scatters_chart(p_png, p_svg, train_rows)
                    self.assertEqual(mock_ax.scatter.call_count, 1)
                    scatter_xs = mock_ax.scatter.call_args[0][0]
                    self.assertEqual(scatter_xs, [20.0, 60.0])
                    mock_ax.set_title.assert_called_with("MSSubClass vs SalePrice", fontsize=11, fontweight="bold")
                    self.assertTrue(p_png.exists())

    def test_scatters_chart_with_matplotlib_all_categorical_fallback(self):
        """Verify that when HAS_MATPLOTLIB is True and all fallback predictors are categorical,
        it does not raise ValueError and gracefully outputs placeholder figures.
        """
        import tools.eda.full_ames_eda as eda

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            p_png = out_dir / "fig07_scatters.png"
            p_svg = out_dir / "fig07_scatters.svg"

            train_rows = [
                {"Id": "1", "Alley": "Grvl", "SalePrice": "100000"},
                {"Id": "2", "Alley": "Pave", "SalePrice": "200000"},
            ]

            numeric_preds = eda._get_numeric_predictors(train_rows)
            self.assertEqual(numeric_preds, [])

            correlations = eda.calculate_numeric_correlations(["Id", "Alley", "SalePrice"], train_rows)
            obs = eda._describe_saleprice_associations(train_rows, correlations)
            self.assertIn("未檢測到可用於散佈圖之數值解釋變數", obs)
            self.assertNotIn("Alley", obs)

            if eda.HAS_MATPLOTLIB:
                eda._render_scatters_chart(p_png, p_svg, train_rows)
                self.assertTrue(p_png.exists())
                self.assertTrue(p_svg.exists())
            else:
                from unittest.mock import MagicMock
                mock_plt = MagicMock()
                mock_fig = MagicMock()
                mock_ax = MagicMock()
                mock_plt.subplots.return_value = (mock_fig, mock_ax)

                def fake_savefig(target, *args, **kwargs):
                    Path(target).write_bytes(b"\x89PNG\r\n\x1a\nfake_png")

                mock_fig.savefig.side_effect = fake_savefig

                with patch.object(eda, "HAS_MATPLOTLIB", True), patch.object(eda, "plt", mock_plt, create=True):
                    eda._render_scatters_chart(p_png, p_svg, train_rows)
                    mock_ax.text.assert_called_once()
                    self.assertIn("No numeric predictors", mock_ax.text.call_args[0][2])
                    self.assertTrue(p_png.exists())

    def test_recognizes_literal_na_string_as_missing_in_full_eda(self):
        """Verify full EDA treats literal 'NA' as missing in inventory and report."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)
            output = local / "research" / "phase2-eda"

            (datasets / "train.csv").write_text(
                "Id,MSSubClass,LotFrontage,Alley,SalePrice\n"
                "1,20,60,NA,100000\n"
                "2,20,NA,Grvl,200000\n"
            )
            (datasets / "test.csv").write_text(
                "Id,MSSubClass,LotFrontage,Alley\n"
                "3,20,70,NA\n"
            )
            (datasets / "sample_submission.csv").write_text(
                "Id,SalePrice\n"
                "3,150000\n"
            )
            (datasets / "data_description.txt").write_text(
                "MSSubClass: Dwelling type\n"
                "LotFrontage: Linear feet\n"
                "Alley: Alley access\n"
                "       NA\tNo alley access\n"
            )

            res = run(datasets, output, "2026-10-24", True, local_root=local)
            with (output / "field_manifest.json").open() as f:
                manifest = json.load(f)
            lf = next(m for m in manifest if m["name"] == "LotFrontage")
            self.assertEqual(lf["train_missing_count"], 1)
            self.assertEqual(lf["test_missing_count"], 0)
            self.assertTrue(lf["dtype"].startswith("numeric"))

            alley = next(m for m in manifest if m["name"] == "Alley")
            self.assertEqual(alley["train_missing_count"], 1)
            self.assertEqual(alley["test_missing_count"], 1)
            self.assertTrue(alley["is_structural_missing_candidate"])

            report_text = (output / "report.md").read_text(encoding="utf-8")
            self.assertIn("| `LotFrontage` | 1 | 50.00% | 0 | 0.00% | 真實未記錄缺漏 (需插補) |", report_text)
            self.assertIn("| `Alley` | 1 | 50.00% | 1 | 100.00% | 結構性缺失 (特徵不存在) |", report_text)

    def test_configurable_local_root_option_in_full_eda(self):
        """Verify full EDA supports configurable local_root without explicit data/output dirs."""
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "custom_local"
            datasets = local / "datasets"
            datasets.mkdir(parents=True)

            (datasets / "train.csv").write_text("Id,MSSubClass,SalePrice\n1,20,100000\n")
            (datasets / "test.csv").write_text("Id,MSSubClass\n2,20\n")
            (datasets / "sample_submission.csv").write_text("Id,SalePrice\n2,100000\n")
            (datasets / "data_description.txt").write_text("MSSubClass: Dwelling type\n")

            res = run(None, None, "2026-10-24", True, local_root=local)
            self.assertTrue((local / "research" / "phase2-eda" / "report.md").exists())
            self.assertTrue((local / "research" / "phase2-eda" / "profile.json").exists())
            self.assertEqual(res["status"], "descriptive_profile_generated_pending_review")


if __name__ == "__main__":
    unittest.main()
