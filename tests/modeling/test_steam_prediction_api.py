from __future__ import annotations

import csv
import io
import json
import math
import os
import socket
import ssl
import threading
import unittest
from http.client import HTTPConnection
from http.server import HTTPServer
from unittest.mock import patch

import numpy as np

from housing_regression import steam_prediction_api as steam
from housing_regression.steam_model_compat import MODEL_INPUT_FIELDS


def _schema():
    return json.loads((steam._project_root() / steam.SCHEMA_RELATIVE_PATH).read_text(encoding="utf-8"))


def _valid_inputs():
    return {
        "genres": ["Indie", "Adventure"],
        "price": 9.99,
        "required_age": 0,
        "dlc_count": 0,
        "achievements": 30,
        "release_year": 2024,
        "windows": True,
        "mac": False,
        "linux": False,
        "genre_count": 2,
        "category_count": 1,
        "tag_count": 10,
        "supported_language_count": 10,
        "full_audio_language_count": 1,
        "has_english": True,
        "has_traditional_chinese": False,
        "discount": 0,
        "developer_count": 1,
        "publisher_count": 1,
        "screenshot_count": 4,
        "movie_count": 0,
        "has_website": True,
    }


class SyntheticModel:
    def predict(self, frame):
        if len(frame) != 1 or tuple(frame.columns) != MODEL_INPUT_FIELDS:
            raise AssertionError("unexpected model input structure")
        return np.asarray([math.log1p(12.5)])


class SyntheticBlobResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _limit):
        return self.payload


class SteamPredictionApiTests(unittest.TestCase):
    def setUp(self):
        steam.reset_runtime_for_tests()

    def tearDown(self):
        steam.reset_runtime_for_tests()

    def test_contract_sha_and_identity_are_pinned(self):
        payload = steam.load_schema_bytes()
        self.assertEqual(steam.hashlib.sha256(payload).hexdigest(), steam.SCHEMA_SHA256)
        schema = json.loads(payload)
        self.assertEqual(schema["case_id"], "steam-review-multiplier")
        self.assertEqual(len(schema["input_fields"]), 22)
        self.assertEqual(set(schema["required"]), set(schema["input_fields"]) | {"review_count"})

    def test_private_blob_fetch_uses_passed_oidc_token_and_pinned_digest(self):
        payload = b"synthetic-private-model"
        expected_sha = steam.hashlib.sha256(payload).hexdigest()
        captured = {}

        def opener(request, timeout):
            captured["authorization"] = request.get_header("Authorization")
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return SyntheticBlobResponse(payload)

        with patch.dict(os.environ, {"BLOB_STORE_ID": "store_Test123"}, clear=False), patch.object(
            steam, "MODEL_SHA256", expected_sha
        ), patch.object(steam, "MODEL_BLOB_PATH", f"steam/run-01/{expected_sha}/model.bin"):
            result = steam._read_private_model_bytes("synthetic-oidc-token", opener=opener)
        self.assertEqual(result, payload)
        self.assertEqual(captured["authorization"], "Bearer synthetic-oidc-token")
        self.assertIn(expected_sha, captured["url"])
        self.assertEqual(captured["timeout"], 8)

    def test_runtime_failure_logs_only_fixed_stage_and_safe_category(self):
        environment = {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": steam._PREVIEW_BRANCH,
        }
        private_error = "private-detail-must-not-be-logged"
        blob_error = __import__("urllib.error", fromlist=["HTTPError"]).HTTPError(
            "https://private.invalid/secret-path", 403, private_error, None, None
        )
        with patch.dict(os.environ, environment, clear=False), patch.object(
            steam, "load_schema_bytes", return_value=b"{}"
        ), patch.object(steam, "_read_private_model_bytes", side_effect=blob_error):
            with self.assertLogs(steam._LOGGER, level="ERROR") as captured:
                with self.assertRaises(Exception):
                    steam.load_runtime("synthetic-oidc-token")
        self.assertEqual(
            captured.output,
            ["ERROR:housing_regression.steam_prediction_api:steam_runtime_load_failed stage=private_model_fetch_and_digest category=private_blob_auth_rejected"],
        )
        self.assertNotIn(private_error, "\n".join(captured.output))

    def test_blob_transport_diagnostics_are_whitelisted(self):
        self.assertEqual(
            steam._safe_load_failure_category(__import__("urllib.error", fromlist=["URLError"]).URLError(
                ssl.SSLCertVerificationError("sensitive tls detail")
            )),
            "private_blob_tls_certificate_error",
        )
        self.assertEqual(
            steam._safe_load_failure_category(__import__("urllib.error", fromlist=["URLError"]).URLError(
                socket.gaierror("sensitive dns detail")
            )),
            "private_blob_dns_error",
        )

    def test_valid_input_runs_pipeline_and_calculates_ownership_baseline(self):
        runtime = steam.SteamPredictionRuntime(SyntheticModel(), _schema(), b"synthetic")
        result = runtime.predict(_valid_inputs(), 250)
        self.assertEqual(result["predicted_k"], 12.5)
        self.assertEqual(result["estimated_ownership"], 3125)
        self.assertEqual(result["fixed_k_30_ownership"], 7500)
        self.assertEqual(result["run_id"], steam.RUN_ID)
        self.assertEqual(result["model_sha256"], steam.MODEL_SHA256)

    def test_missing_extra_fields_and_unknown_genres_are_rejected(self):
        schema = _schema()
        values = _valid_inputs()
        values.pop("price")
        with self.assertRaises(steam.SteamPredictionError) as error:
            steam.validate_inputs(values, 20, schema)
        self.assertEqual(error.exception.code, "invalid_fields")
        values = _valid_inputs() | {"untrusted": 1}
        with self.assertRaises(steam.SteamPredictionError):
            steam.validate_inputs(values, 20, schema)
        values = _valid_inputs() | {"genres": ["not-a-contract-genre"]}
        with self.assertRaises(steam.SteamPredictionError) as error:
            steam.validate_inputs(values, 20, schema)
        self.assertEqual(error.exception.code, "invalid_category")

    def test_nonfinite_and_out_of_contract_numbers_are_rejected(self):
        schema = _schema()
        values = _valid_inputs() | {"price": float("nan")}
        with self.assertRaises(steam.SteamPredictionError) as error:
            steam.validate_inputs(values, 20, schema)
        self.assertEqual(error.exception.code, "invalid_number")
        values = _valid_inputs() | {"release_year": 0}
        with self.assertRaises(steam.SteamPredictionError):
            steam.validate_inputs(values, 20, schema)
        with self.assertRaises(steam.SteamPredictionError):
            steam.validate_inputs(_valid_inputs(), 0, schema)

    def test_batch_preserves_row_order_and_isolates_invalid_rows(self):
        runtime = steam.SteamPredictionRuntime(SyntheticModel(), _schema(), b"synthetic")
        fields = [*MODEL_INPUT_FIELDS, "review_count"]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        row = _valid_inputs() | {"genres": "Indie|Adventure", "review_count": 250}
        writer.writerow(row)
        writer.writerow(row | {"price": "not-number", "review_count": 500})
        result = steam.predict_csv_batch(runtime, output.getvalue().encode("utf-8"))
        self.assertEqual((result["total_rows"], result["success_rows"], result["error_rows"]), (2, 1, 1))
        self.assertEqual([item["row_number"] for item in result["rows"]], [2, 3])
        self.assertEqual(result["rows"][0]["predicted_k"], 12.5)
        self.assertEqual(result["rows"][1]["error_code"], "invalid_number")

    def test_batch_rejects_duplicate_missing_extra_and_oversized_row_sets(self):
        runtime = steam.SteamPredictionRuntime(SyntheticModel(), _schema(), b"synthetic")
        with self.assertRaises(steam.SteamPredictionError) as error:
            steam.predict_csv_batch(runtime, b"genres,genres\nIndie,Action\n")
        self.assertEqual(error.exception.code, "duplicate_columns")
        with self.assertRaises(steam.SteamPredictionError):
            steam.predict_csv_batch(runtime, b"genres,price\nIndie,5\n")
        fields = [*MODEL_INPUT_FIELDS, "review_count"]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for _ in range(steam.MAX_BATCH_ROWS + 1):
            writer.writerow(_valid_inputs() | {"genres": "Indie", "review_count": 10})
        with self.assertRaises(steam.SteamPredictionError) as error:
            steam.predict_csv_batch(runtime, output.getvalue().encode("utf-8"))
        self.assertEqual(error.exception.code, "too_many_rows")

    def test_deployment_gate_is_exact_and_fail_closed(self):
        with patch.dict("os.environ", {"VERCEL_ENV": "preview", "VERCEL_GIT_COMMIT_REF": steam._PREVIEW_BRANCH}, clear=False):
            self.assertTrue(steam.deployment_is_enabled())
            self.assertFalse(steam.authorized_host("attacker.example"))
        with patch.dict("os.environ", {"VERCEL_ENV": "production", "VERCEL_GIT_COMMIT_REF": "deploy", "REGSCOPE_STEAM_PRODUCTION_INFERENCE": "0"}, clear=False):
            self.assertFalse(steam.deployment_is_enabled())

    def _request(self, method, path, body=None, headers=None):
        server = HTTPServer(("127.0.0.1", 0), __import__("housing_regression.vercel_car_function", fromlist=["create_handler"]).create_handler())
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection(*server.server_address, timeout=3)
            request_headers = {"Host": "steam-preview.example.vercel.app", **(headers or {})}
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            status = response.status
            document = json.loads(response.read())
            connection.close()
            return status, document
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_schema_and_single_prediction_routes_dispatch_by_case_id(self):
        runtime = steam.SteamPredictionRuntime(SyntheticModel(), _schema(), b"synthetic")
        environment = {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": steam._PREVIEW_BRANCH,
            "VERCEL_URL": "steam-preview.example.vercel.app",
        }
        with patch.dict(os.environ, environment, clear=False), patch(
            "housing_regression.vercel_car_function._steam_runtime", return_value=runtime
        ) as runtime_loader:
            oidc_headers = {"x-vercel-oidc-token": "synthetic-oidc-token"}
            status, schema_doc = self._request(
                "GET", "/api/schema?case_id=steam-review-multiplier", headers=oidc_headers
            )
            self.assertEqual(status, 200)
            self.assertEqual(schema_doc["model_id"], steam.MODEL_ID)
            payload = {
                "case_id": steam.CASE_ID,
                "model_id": steam.MODEL_ID,
                "model_version": steam.MODEL_VERSION,
                "inputs": _valid_inputs(),
                "review_count": 250,
            }
            status, prediction = self._request(
                "POST", "/api/predict", json.dumps(payload),
                {"Origin": "https://steam-preview.example.vercel.app", "Content-Type": "application/json", **oidc_headers},
            )
            self.assertEqual(status, 200)
            self.assertEqual(prediction["predicted_k"], 12.5)
            self.assertEqual(prediction["estimated_ownership"], 3125)
            runtime_loader.assert_called_with("synthetic-oidc-token")

    def test_batch_route_dispatches_and_untrusted_origin_is_rejected_before_body_read(self):
        runtime = steam.SteamPredictionRuntime(SyntheticModel(), _schema(), b"synthetic")
        environment = {
            "VERCEL_ENV": "preview",
            "VERCEL_GIT_COMMIT_REF": steam._PREVIEW_BRANCH,
            "VERCEL_URL": "steam-preview.example.vercel.app",
        }
        fields = [*MODEL_INPUT_FIELDS, "review_count"]
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerow(_valid_inputs() | {"genres": "Indie|Adventure", "review_count": 250})
        headers = {
            "Origin": "https://steam-preview.example.vercel.app",
            "Content-Type": "text/csv",
            "x-vercel-oidc-token": "synthetic-oidc-token",
        }
        with patch.dict(os.environ, environment, clear=False), patch(
            "housing_regression.vercel_car_function._steam_runtime", return_value=runtime
        ) as runtime_loader:
            status, result = self._request(
                "POST", "/api/predict-batch?case_id=steam-review-multiplier", output.getvalue(), headers
            )
            self.assertEqual(status, 200)
            self.assertEqual((result["success_rows"], result["error_rows"]), (1, 0))
            self.assertEqual(result["rows"][0]["row_number"], 2)
            runtime_loader.assert_called_with("synthetic-oidc-token")
            status, rejected = self._request(
                "POST", "/api/predict-batch?case_id=steam-review-multiplier", output.getvalue(),
                {**headers, "Origin": "https://attacker.example"},
            )
            self.assertEqual(status, 403)
            self.assertEqual(rejected["error"]["code"], "origin_rejected")


if __name__ == "__main__":
    unittest.main()
