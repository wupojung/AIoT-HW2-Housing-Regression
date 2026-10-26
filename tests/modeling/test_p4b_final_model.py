"""Focused synthetic tests for the serialized final P4-B model wrapper."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from housing_regression.modeling.p4b_final_model import FinalP4BDevelopmentModel


class _SyntheticPipeline:
    is_fitted = True

    def transform(self, rows, split_name):
        self.split_name = split_name
        self.rows = rows
        return SimpleNamespace(
            feature_names=["b", "a", "unused"],
            to_numpy=lambda: np.asarray([[2.0, 3.0, 99.0] for _ in rows]),
        )


class FinalP4BDevelopmentModelTests(unittest.TestCase):
    def test_predict_uses_selected_feature_order_and_fitted_transform(self):
        pipeline = _SyntheticPipeline()
        model = FinalP4BDevelopmentModel(
            preprocessing_pipeline=pipeline,
            selected_feature_names=("a", "b"),
            ols_coefficients=np.asarray([10.0, 100.0, 1.0]),
            metadata={},
        )

        predictions = model.predict([{"x": "synthetic"}, {"x": "synthetic-2"}])

        np.testing.assert_allclose(predictions, [312.0, 312.0])
        self.assertEqual(pipeline.split_name, "final_model_predict")

    def test_predict_rejects_rows_containing_target(self):
        model = FinalP4BDevelopmentModel(
            preprocessing_pipeline=_SyntheticPipeline(),
            selected_feature_names=("a", "b"),
            ols_coefficients=np.asarray([0.0, 1.0, 1.0]),
            metadata={},
        )

        with self.assertRaisesRegex(ValueError, "must not contain the SalePrice target"):
            model.predict([{"SalePrice": 123.0}])

    def test_constructor_rejects_invalid_coefficients(self):
        with self.assertRaisesRegex(ValueError, "must be finite"):
            FinalP4BDevelopmentModel(
                preprocessing_pipeline=_SyntheticPipeline(),
                selected_feature_names=("a", "b"),
                ols_coefficients=np.asarray([0.0, np.nan, 1.0]),
                metadata={},
            )


if __name__ == "__main__":
    unittest.main()
