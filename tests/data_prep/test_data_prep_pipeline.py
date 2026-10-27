"""Unit tests for Ames Housing Data Preparation pipeline."""

from __future__ import annotations

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
    NOMINAL_COLUMNS,
    NUMERIC_COLUMNS,
    ORDINAL_COLUMNS,
    STRUCTURAL_ABSENCE_COLUMNS,
    TARGET_COLUMN,
    AmesDataPreparationPipeline,
    split_labeled_dataset,
)


class DataPreparationPipelineTests(unittest.TestCase):
    """Synthetic tests verifying data isolation, leakage prevention, and encodings."""

    def test_deterministic_split_ratios_and_no_leakage(self):
        """Verify 80/20 split produces exact partitions with zero overlap and reproducibility."""
        synthetic_rows = [{"Id": str(i), "SalePrice": float(100000 + i * 100)} for i in range(1460)]
        train_rows, val_rows = split_labeled_dataset(synthetic_rows, val_fraction=0.2, random_state=42)

        self.assertEqual(len(train_rows), 1168)
        self.assertEqual(len(val_rows), 292)

        train_ids = {r["Id"] for r in train_rows}
        val_ids = {r["Id"] for r in val_rows}
        self.assertEqual(len(train_ids & val_ids), 0, "Train and validation splits must not overlap")

        # Verify reproducibility with same seed
        train_rows_2, val_rows_2 = split_labeled_dataset(synthetic_rows, val_fraction=0.2, random_state=42)
        self.assertEqual([r["Id"] for r in train_rows], [r["Id"] for r in train_rows_2])

    def test_target_and_id_isolation(self):
        """Verify Id and SalePrice are completely excluded from the predictor matrix X."""
        synthetic_train = [
            {"Id": "1", "SalePrice": "200000", "LotArea": "8000", "MSSubClass": "20", "Neighborhood": "CollgCr"},
            {"Id": "2", "SalePrice": "150000", "LotArea": "9000", "MSSubClass": "60", "Neighborhood": "Veenker"},
        ]
        pipeline = AmesDataPreparationPipeline()
        result = pipeline.fit_transform(synthetic_train, split_name="train")

        self.assertNotIn("Id", pipeline.feature_names)
        self.assertNotIn("SalePrice", pipeline.feature_names)
        self.assertNotIn("Id", result.features[0])
        self.assertNotIn("SalePrice", result.features[0])
        self.assertEqual(result.ids, ["1", "2"])
        self.assertEqual(result.y, [200000.0, 150000.0])

    def test_leakage_boundary_held_out_data_does_not_affect_fit(self):
        """Verify transforming held-out data with extreme values does not alter pipeline parameters."""
        synthetic_train = [
            {"LotFrontage": "60", "LotArea": "8000", "MSSubClass": "20", "Neighborhood": "CollgCr"},
            {"LotFrontage": "80", "LotArea": "10000", "MSSubClass": "20", "Neighborhood": "CollgCr"},
        ]
        pipeline = AmesDataPreparationPipeline()
        pipeline.fit(synthetic_train)

        # Fitted median for LotFrontage should be (60 + 80) / 2 = 70.0
        self.assertEqual(pipeline.numeric_impute_values["LotFrontage"], 70.0)

        # Transform held-out validation data with an extreme value and missing values
        held_out_val = [
            {"LotFrontage": "NA", "LotArea": "500000"},  # Missing LotFrontage should receive train median (70.0)
            {"LotFrontage": "999999", "LotArea": "10000"},
        ]
        val_res = pipeline.transform(held_out_val, split_name="val")

        # Imputed value must match the original training median, completely unaffected by 999999
        self.assertEqual(val_res.features[0]["LotFrontage"], 70.0)
        self.assertEqual(pipeline.numeric_impute_values["LotFrontage"], 70.0)

    def test_unseen_category_handling_without_crash(self):
        """Verify nominal one-hot handles unknown levels gracefully with all-zero dummy indicators."""
        synthetic_train = [
            {"Neighborhood": "CollgCr", "MSSubClass": "20"},
            {"Neighborhood": "Veenker", "MSSubClass": "60"},
        ]
        pipeline = AmesDataPreparationPipeline()
        pipeline.fit(synthetic_train)

        self.assertIn("Neighborhood_CollgCr", pipeline.feature_names)
        self.assertIn("Neighborhood_Veenker", pipeline.feature_names)
        self.assertNotIn("Neighborhood_UnknownPlace", pipeline.feature_names)

        # Held-out row with an unseen neighborhood and unseen MSSubClass
        held_out_test = [
            {"Neighborhood": "UnknownPlace", "MSSubClass": "150"},
        ]
        test_res = pipeline.transform(held_out_test, split_name="test")

        # Check that both known dummy columns are 0.0
        self.assertEqual(test_res.features[0]["Neighborhood_CollgCr"], 0.0)
        self.assertEqual(test_res.features[0]["Neighborhood_Veenker"], 0.0)

        # Check that unseen category was properly tracked in the transform result
        unseen_cols = [item["column"] for item in test_res.unseen_categories]
        self.assertIn("Neighborhood", unseen_cols)
        self.assertIn("MSSubClass", unseen_cols)

    def test_structural_absence_15_fields_handling(self):
        """Verify the 15 structural absence fields map to documented sentinels/indicators/0."""
        # Row representing a property with NO garage, NO basement, NO pool, NO fence, NO fireplace
        row_no_facilities = {
            "Alley": "NA",
            "PoolQC": "NA",
            "Fence": "NA",
            "MiscFeature": "NA",
            "FireplaceQu": "NA",
            "Fireplaces": "0",
            "GarageType": "NA",
            "GarageYrBlt": "NA",
            "GarageFinish": "NA",
            "GarageQual": "NA",
            "GarageCond": "NA",
            "BsmtQual": "NA",
            "BsmtCond": "NA",
            "BsmtExposure": "NA",
            "BsmtFinType1": "NA",
            "BsmtFinType2": "NA",
            "TotalBsmtSF": "0",
            "PoolArea": "0",
        }
        pipeline = AmesDataPreparationPipeline()
        pipeline.fit([row_no_facilities])
        res = pipeline.transform([row_no_facilities], split_name="test")

        f = res.features[0]

        # Structural indicators should all indicate absence (0.0)
        self.assertEqual(f["HasGarage"], 0.0)
        self.assertEqual(f["HasBasement"], 0.0)
        self.assertEqual(f["HasFireplace"], 0.0)
        self.assertEqual(f["HasPool"], 0.0)
        self.assertEqual(f["HasFence"], 0.0)
        self.assertEqual(f["HasAlley"], 0.0)
        self.assertEqual(f["HasMiscFeature"], 0.0)

        # Ordinal structural absence should be score 0.0
        self.assertEqual(f["PoolQC"], 0.0)
        self.assertEqual(f["Fence"], 0.0)
        self.assertEqual(f["FireplaceQu"], 0.0)
        self.assertEqual(f["GarageQual"], 0.0)
        self.assertEqual(f["GarageCond"], 0.0)
        self.assertEqual(f["GarageFinish"], 0.0)
        self.assertEqual(f["BsmtQual"], 0.0)
        self.assertEqual(f["BsmtCond"], 0.0)
        self.assertEqual(f["BsmtExposure"], 0.0)
        self.assertEqual(f["BsmtFinType1"], 0.0)
        self.assertEqual(f["BsmtFinType2"], 0.0)

        # GarageYrBlt should receive documented sentinel (0.0)
        self.assertEqual(f["GarageYrBlt"], 0.0)

    def test_masvnr_missingness_distinguishable_from_genuine_none_and_zero(self):
        """Verify genuine missing MasVnrType/Area reproduce collision and are only distinguished by flags."""
        # 1. Fit training records where nominal mode is explicitly 'None' and numeric median is 0.0
        # (3 rows with 'None'/0.0, 1 row with 'BrkFace'/150.0)
        train_records = [
            {"Id": "tr1", "MasVnrType": "None", "MasVnrArea": "0", "MSSubClass": "20"},
            {"Id": "tr2", "MasVnrType": "None", "MasVnrArea": "0", "MSSubClass": "20"},
            {"Id": "tr3", "MasVnrType": "None", "MasVnrArea": "0", "MSSubClass": "20"},
            {"Id": "tr4", "MasVnrType": "BrkFace", "MasVnrArea": "150", "MSSubClass": "20"},
        ]
        pipeline = AmesDataPreparationPipeline()
        pipeline.fit(train_records)

        # Confirm that training fit actually learned mode='None' and median=0.0
        self.assertEqual(pipeline.nominal_impute_values["MasVnrType"], "None")
        self.assertEqual(pipeline.numeric_impute_values["MasVnrArea"], 0.0)

        # 2. Test records to transform:
        # Row A: Genuine physical absence (MasVnrType='None', MasVnrArea='0')
        row_genuine_none = {"Id": "te1", "MasVnrType": "None", "MasVnrArea": "0", "MSSubClass": "20"}
        # Row B: Unrecorded/non-structural missingness (MasVnrType='NA', MasVnrArea='NA')
        row_unrecorded_missing = {"Id": "te2", "MasVnrType": "NA", "MasVnrArea": "NA", "MSSubClass": "20"}

        result = pipeline.transform([row_genuine_none, row_unrecorded_missing], split_name="test")
        f_none = result.features[0]
        f_missing = result.features[1]

        # 3. Assert that imputed type/area values are IDENTICAL (the collision):
        # Both receive MasVnrType_None = 1.0, MasVnrType_BrkFace = 0.0, and MasVnrArea = 0.0
        self.assertEqual(f_none["MasVnrType_None"], 1.0)
        self.assertEqual(f_missing["MasVnrType_None"], 1.0)
        self.assertEqual(f_none["MasVnrType_BrkFace"], 0.0)
        self.assertEqual(f_missing["MasVnrType_BrkFace"], 0.0)
        self.assertEqual(f_none["MasVnrArea"], 0.0)
        self.assertEqual(f_missing["MasVnrArea"], 0.0)

        # 4. Assert that ONLY the two missingness flags distinguish them:
        self.assertEqual(f_none["MasVnrType_is_missing"], 0.0)
        self.assertEqual(f_none["MasVnrArea_is_missing"], 0.0)
        self.assertEqual(f_missing["MasVnrType_is_missing"], 1.0)
        self.assertEqual(f_missing["MasVnrArea_is_missing"], 1.0)

        differing_features = {k for k in f_none if f_none[k] != f_missing[k]}
        self.assertEqual(
            differing_features,
            {"MasVnrType_is_missing", "MasVnrArea_is_missing"},
            "Imputed values must collide and ONLY the two missingness indicators should distinguish them",
        )

        # 5. Verify held-out data in transform does not affect fitted parameters
        held_out_extreme = [{"MasVnrType": "Stone", "MasVnrArea": "999999", "MSSubClass": "20"}]
        pipeline.transform(held_out_extreme, split_name="test")
        self.assertEqual(pipeline.nominal_impute_values["MasVnrType"], "None")
        self.assertEqual(pipeline.numeric_impute_values["MasVnrArea"], 0.0)


if __name__ == "__main__":
    unittest.main()
