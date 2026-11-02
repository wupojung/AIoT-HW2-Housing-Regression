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

    def test_canonical_deployment_origin_is_accepted(self):
        with patch.dict(os.environ, {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": vercel_car_function._BRANCH,
            "VERCEL_URL": "regscope-deployment.example.vercel.app",
        }, clear=False):
            self.assertTrue(vercel_car_function._origin_is_authorized(
                "https://regscope-deployment.example.vercel.app", required=True
            ))

    def test_exact_preview_branch_alias_is_accepted(self):
        with patch.dict(os.environ, {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": vercel_car_function._BRANCH,
            "VERCEL_URL": "regscope-deployment.example.vercel.app",
        }, clear=False):
            self.assertTrue(vercel_car_function._origin_is_authorized(
                f"https://{vercel_car_function._PREVIEW_BRANCH_ALIAS}", required=True
            ))

    def test_unrelated_origin_and_missing_post_origin_are_rejected(self):
        with patch.dict(os.environ, {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": vercel_car_function._BRANCH,
            "VERCEL_URL": "regscope-deployment.example.vercel.app",
        }, clear=False):
            self.assertFalse(vercel_car_function._origin_is_authorized(
                "https://attacker.example", required=True
            ))
            self.assertFalse(vercel_car_function._origin_is_authorized(None, required=True))

    def test_branch_alias_is_rejected_outside_authorized_preview_branch(self):
        alias = f"https://{vercel_car_function._PREVIEW_BRANCH_ALIAS}"
        with patch.dict(os.environ, {
            "VERCEL_ENV": "production",
            "VERCEL_GIT_COMMIT_REF": "deploy",
            "VERCEL_URL": "regscope-deployment.example.vercel.app",
        }, clear=False):
            self.assertFalse(vercel_car_function._origin_is_authorized(alias, required=True))
        with patch.dict(os.environ, {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": "another-preview-branch",
            "VERCEL_URL": "regscope-deployment.example.vercel.app",
        }, clear=False):
            self.assertFalse(vercel_car_function._origin_is_authorized(alias, required=True))

    def test_production_gate_requires_environment_branch_and_explicit_flag(self):
        base = {
            "VERCEL_ENV": "production",
            "VERCEL_GIT_COMMIT_REF": "deploy",
            "REGSCOPE_CAR_PRODUCTION_INFERENCE": "1",
        }
        with patch.dict(os.environ, base, clear=False):
            self.assertTrue(vercel_car_function._production_branch_allowed())
        for override in (
            {"VERCEL_ENV": "preview"},
            {"VERCEL_GIT_COMMIT_REF": "main"},
            {"REGSCOPE_CAR_PRODUCTION_INFERENCE": "0"},
            {"REGSCOPE_CAR_PRODUCTION_INFERENCE": "true"},
        ):
            environment = {**base, **override}
            with patch.dict(os.environ, environment, clear=False):
                self.assertFalse(vercel_car_function._production_branch_allowed())

    def test_production_origin_is_exact_and_requires_production_gate(self):
        allowed = {
            "VERCEL_ENV": "production",
            "VERCEL_GIT_COMMIT_REF": "deploy",
            "REGSCOPE_CAR_PRODUCTION_INFERENCE": "1",
        }
        with patch.dict(os.environ, allowed, clear=False):
            self.assertTrue(vercel_car_function._origin_is_authorized(
                vercel_car_function._PRODUCTION_ORIGIN, required=True
            ))
            self.assertFalse(vercel_car_function._origin_is_authorized(
                "https://regscope-aiot.vercel.app.evil.example", required=True
            ))
            self.assertFalse(vercel_car_function._origin_is_authorized(None, required=True))
            self.assertFalse(vercel_car_function._origin_is_authorized(
                "https://regscope-deployment.example.vercel.app", required=True
            ))
        with patch.dict(os.environ, {
            **allowed,
            "REGSCOPE_CAR_PRODUCTION_INFERENCE": "0",
        }, clear=False):
            self.assertFalse(vercel_car_function._origin_is_authorized(
                vercel_car_function._PRODUCTION_ORIGIN, required=True
            ))

    def test_production_runtime_fails_closed_without_asset_flag(self):
        with patch.dict(os.environ, {
            "VERCEL_ENV": "production",
            "VERCEL_GIT_COMMIT_REF": "deploy",
            "REGSCOPE_CAR_PRODUCTION_INFERENCE": "1",
        }, clear=False):
            with patch.object(vercel_car_function, "_decode_assets", side_effect=PredictionInputSchemaError("assets unavailable")) as decode_assets:
                with self.assertRaisesRegex(PredictionInputSchemaError, "assets unavailable"):
                    vercel_car_function._runtime()
        decode_assets.assert_called_once_with()
        self.assertIsNone(vercel_car_function._RUNTIME)

    def test_production_and_preview_gates_cannot_cross_authorize_origins(self):
        with patch.dict(os.environ, {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": vercel_car_function._BRANCH,
            "VERCEL_URL": "regscope-deployment.example.vercel.app",
            "REGSCOPE_CAR_PRODUCTION_INFERENCE": "1",
        }, clear=False):
            self.assertFalse(vercel_car_function._origin_is_authorized(
                vercel_car_function._PRODUCTION_ORIGIN, required=True
            ))

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
