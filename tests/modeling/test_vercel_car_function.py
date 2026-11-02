from __future__ import annotations

import os
import unittest
import csv
import io
import json
import threading
from http.client import HTTPConnection
from http.server import HTTPServer
from unittest.mock import patch

from housing_regression import vercel_car_function
from housing_regression.prediction_input_schema import PredictionInputSchemaError


class SyntheticBatchRuntime:
    def __init__(self):
        self.contract = {
            "case_id": "synthetic-car",
            "model_id": "synthetic-model",
            "model_version": "synthetic-v1",
            "source_evidence": {"run_id": "synthetic-run", "configuration_id": "synthetic-config"},
            "input_features": [
                {"name": f"field_{index:02d}", "data_type": "number", "nullable": False}
                for index in range(15)
            ],
        }
        self.schema_sha256 = "c" * 64
        self.schema_bytes = json.dumps(self.contract).encode("utf-8")
        self.calls = []

    def predict(self, inputs):
        self.calls.append(inputs)
        return {"prediction": float(len(self.calls)), "unit": None}


def _synthetic_csv(row_count):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow([f"field_{index:02d}" for index in range(15)])
    for _ in range(row_count):
        writer.writerow([str(index + 1) for index in range(15)])
    return output.getvalue().encode("utf-8")


def _request_batch(payload, origin):
    server = HTTPServer(("127.0.0.1", 0), vercel_car_function.create_handler())
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection(*server.server_address, timeout=3)
        connection.request(
            "POST", "/api/predict-batch", body=payload,
            headers={"Content-Type": "text/csv; charset=utf-8", "Origin": origin},
        )
        response = connection.getresponse()
        status = response.status
        document = json.loads(response.read())
        connection.close()
        return status, document
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request_schema(origin):
    server = HTTPServer(("127.0.0.1", 0), vercel_car_function.create_handler())
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection(*server.server_address, timeout=3)
        connection.request("GET", "/api/schema", headers={"Origin": origin})
        response = connection.getresponse()
        status = response.status
        document = json.loads(response.read())
        connection.close()
        return status, document
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


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

    def test_schema_runtime_failures_log_only_fixed_stage_and_category(self):
        environment = {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": vercel_car_function._BRANCH,
            "VERCEL_URL": "regscope-preview.example.vercel.app",
        }
        cases = (
            (ModuleNotFoundError("private module path /do-not-log"), "import_error"),
            (FileNotFoundError("/private/path/prediction-input-schema.json"), "file_missing"),
        )
        for failure, category in cases:
            with self.subTest(category=category):
                vercel_car_function._RUNTIME = None
                with patch.dict(os.environ, environment, clear=False):
                    with patch.object(
                        vercel_car_function,
                        "_decode_assets",
                        return_value=(b"synthetic-model", b"synthetic-schema", b"synthetic-manifest"),
                    ), patch.object(
                        vercel_car_function,
                        "load_verified_car_runtime",
                        side_effect=failure,
                    ), self.assertLogs(vercel_car_function._LOGGER, level="ERROR") as captured:
                        status, document = _request_schema(
                            "https://regscope-preview.example.vercel.app"
                        )
                self.assertEqual(status, 503)
                self.assertEqual(document["error"]["code"], "model_unavailable")
                self.assertEqual(
                    captured.output,
                    [
                        "ERROR:housing_regression.vercel_car_function:"
                        f"car_runtime_initialization_failed stage=model_contract_load category={category}"
                    ],
                )
                self.assertNotIn("/private/path", " ".join(captured.output))
                self.assertNotIn("/do-not-log", " ".join(captured.output))
                self.assertNotIn("private module path", document["error"]["message"])
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

    def test_production_batch_rejects_row_eleven_before_inference(self):
        runtime = SyntheticBatchRuntime()
        vercel_car_function._RUNTIME = runtime
        environment = {
            "VERCEL_ENV": "production",
            "VERCEL_GIT_COMMIT_REF": "deploy",
            "REGSCOPE_CAR_PRODUCTION_INFERENCE": "1",
        }
        with patch.dict(os.environ, environment, clear=False):
            status, document = _request_batch(
                _synthetic_csv(11), vercel_car_function._PRODUCTION_ORIGIN
            )
        self.assertEqual(status, 413)
        self.assertEqual(document["error"]["code"], "too_many_rows")
        self.assertIn("10", document["error"]["message"])
        self.assertEqual(runtime.calls, [])

    def test_preview_batch_keeps_shared_one_hundred_row_cap(self):
        runtime = SyntheticBatchRuntime()
        vercel_car_function._RUNTIME = runtime
        environment = {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": vercel_car_function._BRANCH,
            "VERCEL_URL": "regscope-preview.example.vercel.app",
        }
        with patch.dict(os.environ, environment, clear=False):
            status, document = _request_batch(
                _synthetic_csv(100), "https://regscope-preview.example.vercel.app"
            )
        self.assertEqual(status, 200)
        self.assertEqual(document["total_rows"], 100)
        self.assertEqual(document["valid_rows"], 100)
        self.assertEqual(len(runtime.calls), 100)


if __name__ == "__main__":
    unittest.main()
