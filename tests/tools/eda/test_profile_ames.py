import tempfile
import unittest
from pathlib import Path

from tools.eda.profile_ames import EXPECTED, run


class ProfileAmesTests(unittest.TestCase):
    def test_blocks_without_owner_terms_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "Confirm Kaggle"):
                run(root, root / "out", "2026-10-24", False)

    def test_missing_files_are_reported_without_eda(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in EXPECTED - {"train.csv"}:
                (root / name).write_text("Id,foo\n1,x\n")
            with self.assertRaisesRegex(FileNotFoundError, "train.csv"):
                run(root, root / "out", "2026-10-24", True)
            self.assertFalse((root / "out").exists())

    def test_profiles_synthetic_data_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "train.csv").write_text("Id,Quality,Alley,SalePrice\n1,5,,100000\n2,7,Gravel,200000\n")
            (root / "test.csv").write_text("Id,Quality,Alley\n3,6,\n2,8,Stone\n")
            (root / "data_description.txt").write_text("Synthetic test dictionary")
            report = run(root, root / "out", "2026-10-24", True)
            train = report["files"][0]
            self.assertEqual(train["shape"], {"rows": 2, "columns": 4})
            self.assertEqual(train["predictor_count_excluding_Id_and_target"], 2)
            self.assertEqual(train["missing"]["columns"], {"Alley": 1})
            self.assertTrue(train["id"]["unique"])
            self.assertEqual(train["missingness_patterns"], [{"missing_fields": ["Alley"], "rows": 1}])
            self.assertEqual(report["schema_checks"]["train_test_id_overlap_count"], 1)
            self.assertFalse(report["schema_checks"]["original_predictor_count_at_least_14"])
            self.assertEqual(len(train["sha256"]), 64)
            self.assertTrue((root / "out/profile.json").exists())
            self.assertTrue((root / "out/train_saleprice_distribution.svg").exists())


if __name__ == "__main__":
    unittest.main()
