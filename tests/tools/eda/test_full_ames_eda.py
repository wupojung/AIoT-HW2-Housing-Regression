import tempfile
import unittest
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
            self.assertTrue((output / "report.md").exists())

            # Verify figures directory and assets
            self.assertTrue((output / "figures").is_dir())
            self.assertTrue((output / "figures/fig01_dataset_overview.svg").exists())
            self.assertTrue((output / "figures/fig02_missingness_overview.svg").exists())
            self.assertTrue((output / "figures/fig03_saleprice_distribution.svg").exists())


if __name__ == "__main__":
    unittest.main()
