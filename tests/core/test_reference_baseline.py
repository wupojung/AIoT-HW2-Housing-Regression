import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python" / "src"))

from housing_regression.data_prep.constants import NOMINAL_COLUMNS, NUMERIC_COLUMNS, ORDINAL_COLUMNS, ORDINAL_LEVELS
from housing_regression.reference_baseline import ReferencePhase3Pipeline, _missing


class ReferenceBaselineTests(unittest.TestCase):
    @staticmethod
    def row(index, mas_vnr_type):
        row = {column: "1" for column in NUMERIC_COLUMNS}
        row.update({column: "A" for column in NOMINAL_COLUMNS})
        row.update({column: next(iter(ORDINAL_LEVELS[column])) for column in ORDINAL_COLUMNS})
        row.update({"Id": str(index), "SalePrice": str(100000 + index), "MasVnrType": mas_vnr_type})
        return row

    def test_na_is_missing_but_literal_none_is_a_category(self):
        self.assertTrue(_missing("NA"))
        self.assertTrue(_missing(""))
        self.assertFalse(_missing("None"))

        rows = [
            self.row(1, "None"),
            self.row(2, "BrkFace"),
            self.row(3, "NA"),
            self.row(4, "BrkFace"),
        ]
        pipeline = ReferencePhase3Pipeline()
        batch = pipeline.fit_transform(rows)
        none_idx = batch.feature_names.index("MasVnrType_None")
        missing_idx = batch.feature_names.index("MasVnrType_is_missing")

        self.assertEqual(batch.matrix[0, none_idx], 1.0)
        self.assertEqual(batch.matrix[2, none_idx], 0.0)
        self.assertEqual(batch.matrix[0, missing_idx], 0.0)
        self.assertEqual(batch.matrix[2, missing_idx], 1.0)
        self.assertFalse(np.isnan(batch.matrix).any())

    def test_validation_transform_uses_training_levels_and_imputers(self):
        training = [self.row(1, "BrkFace"), self.row(2, "Stone"), self.row(3, "BrkFace")]
        validation = [self.row(4, "NA")]
        validation[0]["LotFrontage"] = "NA"
        pipeline = ReferencePhase3Pipeline().fit(training)
        batch = pipeline.transform(validation)

        self.assertEqual(batch.matrix.shape[0], 1)
        self.assertEqual(batch.matrix[0, batch.feature_names.index("LotFrontage")], 1.0)
        self.assertEqual(batch.matrix[0, batch.feature_names.index("MasVnrType_BrkFace")], 1.0)
        self.assertEqual(batch.matrix[0, batch.feature_names.index("MasVnrType_is_missing")], 1.0)


if __name__ == "__main__":
    unittest.main()
