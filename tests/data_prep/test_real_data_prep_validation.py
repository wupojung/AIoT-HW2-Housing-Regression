"""Bounded real-data validation for Ames Housing Data Preparation pipeline."""

from __future__ import annotations

import csv
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.data_prep import (
    ALL_PREDICTOR_COLUMNS,
    ID_COLUMN,
    TARGET_COLUMN,
    AmesDataPreparationPipeline,
    split_labeled_dataset,
)


class RealDataPreparationValidationTests(unittest.TestCase):
    """Bounded validation using the primary checkout local dataset files."""

    @classmethod
    def setUpClass(cls):
        # Look for local datasets directory in repository or primary checkout
        possible_roots = [
            REPO_ROOT / "local" / "datasets",
            REPO_ROOT.parent / "AIoT-HW2-Housing-Regression" / "local" / "datasets",
        ]
        cls.data_dir = None
        for r in possible_roots:
            if (r / "train.csv").is_file() and (r / "test.csv").is_file():
                cls.data_dir = r
                break

        if cls.data_dir is None:
            raise unittest.SkipTest("Primary checkout local/datasets not accessible in this environment.")

        with open(cls.data_dir / "train.csv", "r", encoding="utf-8") as f:
            cls.train_raw = list(csv.DictReader(f))
        with open(cls.data_dir / "test.csv", "r", encoding="utf-8") as f:
            cls.test_raw = list(csv.DictReader(f))

    def test_real_data_split_and_pipeline_completeness(self):
        """Verify real Ames data split, feature dimensions, completeness, and IQR preservation."""
        self.assertEqual(len(self.train_raw), 1460)
        self.assertEqual(len(self.test_raw), 1459)

        # 80/20 train/val split
        train_rows, val_rows = split_labeled_dataset(self.train_raw, val_fraction=0.2, random_state=42)
        self.assertEqual(len(train_rows), 1168)
        self.assertEqual(len(val_rows), 292)

        pipeline = AmesDataPreparationPipeline()
        train_res = pipeline.fit_transform(train_rows, split_name="train")
        val_res = pipeline.transform(val_rows, split_name="val")
        test_res = pipeline.transform(self.test_raw, split_name="test")

        # Check encoded feature counts match across all splits
        self.assertEqual(train_res.n_features, 246)
        self.assertEqual(val_res.n_features, 246)
        self.assertEqual(test_res.n_features, 246)

        # Check feature names are identical and ordered
        self.assertEqual(train_res.feature_names, val_res.feature_names)
        self.assertEqual(train_res.feature_names, test_res.feature_names)

        # Verify zero missing values in all matrices
        for name, res in [("train", train_res), ("validation", val_res), ("test", test_res)]:
            nan_count = sum(sum(1 for v in row if math.isnan(v)) for row in res.feature_matrix)
            self.assertEqual(nan_count, 0, f"Partition {name} has {nan_count} unexpected NaNs")

        # Verify all 61 SalePrice IQR outlier candidates are preserved
        all_prices = sorted([float(r[TARGET_COLUMN]) for r in self.train_raw])
        q1 = all_prices[int(0.25 * len(all_prices))]
        q3 = all_prices[int(0.75 * len(all_prices))]
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        raw_iqr_candidates = [p for p in all_prices if p < lower_fence or p > upper_fence]
        self.assertEqual(len(raw_iqr_candidates), 61)

        combined_y = (train_res.y or []) + (val_res.y or [])
        self.assertEqual(len(combined_y), 1460)
        transformed_iqr_candidates = [p for p in combined_y if p < lower_fence or p > upper_fence]
        self.assertEqual(len(transformed_iqr_candidates), 61)

        # Check expected unseen categories
        val_unseen = [(item["column"], item["unseen_value"]) for item in val_res.unseen_categories]
        test_unseen = [(item["column"], item["unseen_value"]) for item in test_res.unseen_categories]
        self.assertIn(("RoofMatl", "Metal"), val_unseen)
        self.assertIn(("MSSubClass", "150"), test_unseen)


if __name__ == "__main__":
    unittest.main()
