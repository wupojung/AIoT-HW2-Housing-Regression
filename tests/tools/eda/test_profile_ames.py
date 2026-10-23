import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.eda.profile_ames import EXPECTED, run


class ProfileAmesTests(unittest.TestCase):
    def test_blocks_without_owner_terms_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "Confirm Kaggle"):
                run(root, root / "out", "2026-10-24", False)

    def test_missing_files_are_reported_without_eda(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "local"
            data = root / "datasets"
            data.mkdir(parents=True)
            for name in EXPECTED - {"train.csv"}:
                (data / name).write_text("Id,foo\n1,x\n")
            with self.assertRaisesRegex(FileNotFoundError, "train.csv"):
                run(data, root / "research", "2026-10-24", True, local_root=root)
            self.assertFalse((root / "research").exists())

    def test_rejects_output_outside_local(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "local"
            data = root / "datasets"
            data.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "inside ignored local"):
                run(data, Path(temp) / "public", "2026-10-24", True, local_root=root)

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
            test_csv = data / "test.csv"
            test_csv.write_text("Id\n2\n")
            actual = Path.is_symlink

            def simulated_symlink(path):
                return path.absolute() == test_csv.absolute() or actual(path)

            with patch.object(Path, "is_symlink", simulated_symlink):
                with self.assertRaisesRegex(ValueError, "must not be symlinks"):
                    run(data, local / "research", "2026-10-24", True, local_root=local)

    def test_profiles_synthetic_data_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            root = local / "datasets"
            root.mkdir(parents=True)
            (root / "train.csv").write_text("Id,Quality,Alley,SalePrice\n1,5,,100000\n2,7,Gravel,200000\n")
            (root / "test.csv").write_text("Id,Quality,Alley\n3,6,\n2,8,Stone\n")
            (root / "data_description.txt").write_text("Quality: Overall rating\nAlley: Alley access\n")
            report = run(root, local / "research", "2026-10-24", True, local_root=local)
            train = report["files"][0]
            self.assertEqual(train["shape"], {"rows": 2, "columns": 4})
            self.assertEqual(train["predictor_count_excluding_Id_and_target"], 2)
            self.assertEqual(train["missing"]["columns"], {"Alley": 1})
            self.assertTrue(train["id"]["unique"])
            self.assertEqual(train["missingness_patterns"], [{"missing_fields": ["Alley"], "rows": 1}])
            self.assertEqual(report["schema_checks"]["train_test_id_overlap_count"], 1)
            self.assertFalse(report["schema_checks"]["original_predictor_count_at_least_14"])
            self.assertNotIn("Id", train["numeric_summary"])
            self.assertNotIn("Id", train["numeric_correlation_with_target"])
            self.assertEqual(report["data_dictionary_crosswalk"]["field_status"]["Quality"], "definition_present")
            self.assertEqual(report["data_dictionary_crosswalk"]["field_status"]["SalePrice"], "target")
            self.assertEqual(len(train["sha256"]), 64)
            self.assertTrue((local / "research/profile.json").exists())
            self.assertTrue((local / "research/train_saleprice_distribution.svg").exists())


if __name__ == "__main__":
    unittest.main()
