from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from housing_regression import vercel_car_function
from housing_regression.prediction_input_schema import PredictionInputSchemaError


class VercelCarFunctionGateTests(unittest.TestCase):
    def setUp(self):
        vercel_car_function._RUNTIME = None

    def tearDown(self):
        vercel_car_function._RUNTIME = None

    def test_model_loading_is_rejected_outside_exact_preview_branch(self):
        with patch.dict(os.environ, {"VERCEL_ENV": "production", "VERCEL_GIT_COMMIT_REF": "deploy"}, clear=False):
            with patch.object(vercel_car_function, "load_verified_car_runtime") as load_model:
                with self.assertRaises(PermissionError):
                    vercel_car_function._runtime()
        load_model.assert_not_called()

    def test_model_loading_is_rejected_for_other_preview_branch(self):
        with patch.dict(os.environ, {"VERCEL_ENV": "preview", "VERCEL_GIT_COMMIT_REF": "deploy"}, clear=False):
            with patch.object(vercel_car_function, "load_verified_car_runtime") as load_model:
                with self.assertRaises(PermissionError):
                    vercel_car_function._runtime()
        load_model.assert_not_called()

    def test_oversized_encoded_asset_fails_before_archive_decode(self):
        with patch.dict(os.environ, {"REGSCOPE_P6_CAR_RUN03_ASSETS_ZIP_B64": "A" * (64 * 1024 + 1)}, clear=False):
            with self.assertRaises(PredictionInputSchemaError):
                vercel_car_function._decode_assets()

    def test_schema_get_is_the_only_public_asset_style_endpoint(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        routes = (root / "vercel.json").read_text(encoding="utf-8")
        self.assertIn("/api/schema", routes)
        self.assertIn("/api/predict-batch", routes)
        self.assertNotIn("final-model.joblib", routes)
        self.assertNotIn("prediction-input-schema.json", routes)


if __name__ == "__main__":
    unittest.main()
