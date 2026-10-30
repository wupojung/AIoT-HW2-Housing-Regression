from __future__ import annotations

import hashlib
import json
import threading
import unittest
from http.client import HTTPConnection

import numpy as np

from housing_regression.local_car_prediction_api import (
    CarPredictionRuntime,
    PredictionApiError,
    _decode_json,
    _read_regular_file,
    create_local_server,
    validate_inputs,
)


def synthetic_contract():
    return {
        "schema_version": "0.1.0",
        "case_id": "synthetic-car",
        "model_id": "synthetic-model",
        "model_version": "synthetic-v1",
        "model_sha256": "a" * 64,
        "input_feature_count": 2,
        "input_features": [
            {"name": "mileage", "data_type": "number", "required": True, "nullable": False, "options": [], "unknown_category_behavior": None},
            {"name": "make", "data_type": "category", "required": True, "nullable": False, "options": [
                {"value": "SYNTHETIC_A"}, {"value": "SYNTHETIC_B"}
            ], "unknown_category_behavior": "ignore"},
        ],
        "preprocessing_reference": {"raw_input_order": ["mileage", "make"]},
        "source_evidence": {"run_id": "synthetic-run", "configuration_id": "synthetic-config"},
    }


class FakeTransformer:
    def transform(self, frame):
        if list(frame.columns) != ["mileage", "make"]:
            raise AssertionError("input order changed")
        return np.asarray([[float(frame.iloc[0, 0]), 1.0]])


class FakeScaler:
    def transform(self, matrix):
        return matrix


class FakeEstimator:
    def predict(self, matrix):
        return np.asarray([float(matrix[0, 0]) + 10.0])


class LocalCarPredictionApiTests(unittest.TestCase):
    def test_validates_complete_raw_inputs_and_encoder_unknown_policy(self):
        contract = synthetic_contract()
        values = validate_inputs(contract, {"mileage": 123.5, "make": "UNSEEN_SYNTHETIC"})
        self.assertEqual(values, {"mileage": 123.5, "make": "UNSEEN_SYNTHETIC"})

    def test_rejects_missing_extra_and_wrong_types(self):
        contract = synthetic_contract()
        for values, code in [
            ({"mileage": 1}, "field_set_mismatch"),
            ({"mileage": 1, "make": "SYNTHETIC_A", "arbitrary_path": "/tmp/model"}, "field_set_mismatch"),
            ({"mileage": True, "make": "SYNTHETIC_A"}, "invalid_number"),
            ({"mileage": float("inf"), "make": "SYNTHETIC_A"}, "invalid_number"),
            ({"mileage": 1, "make": None}, "null_not_supported"),
            ({"mileage": 1, "make": 42}, "invalid_type"),
        ]:
            with self.subTest(code=code, values=values):
                with self.assertRaises(PredictionApiError) as caught:
                    validate_inputs(contract, values)
                self.assertEqual(caught.exception.code, code)

    def test_unknown_categories_fail_closed_when_encoder_errors(self):
        contract = synthetic_contract()
        contract["input_features"][1]["unknown_category_behavior"] = "error"
        with self.assertRaises(PredictionApiError) as caught:
            validate_inputs(contract, {"mileage": 1, "make": "UNSEEN_SYNTHETIC"})
        self.assertEqual(caught.exception.code, "unknown_category")

    def test_runtime_applies_transform_scaler_mask_and_estimator(self):
        contract = synthetic_contract()
        bundle = {
            "features": ["mileage", "make"],
            "transformer": FakeTransformer(),
            "scaler": FakeScaler(),
            "mask": np.asarray([True, False]),
            "estimator": FakeEstimator(),
            "target": "price",
        }
        runtime = CarPredictionRuntime(contract=contract, bundle=bundle)
        result = runtime.predict({"mileage": 42.0, "make": "SYNTHETIC_A"})
        self.assertEqual(result["prediction"], 52.0)
        self.assertTrue(np.isfinite(result["prediction"]))
        self.assertIsNone(result["unit"])
        self.assertEqual(result["run_id"], "synthetic-run")

    def test_http_local_routes_return_schema_prediction_and_reject_bad_model(self):
        contract = synthetic_contract()
        bundle = {"features": ["mileage", "make"], "transformer": FakeTransformer(), "scaler": FakeScaler(),
                  "mask": np.asarray([True, False]), "estimator": FakeEstimator(), "target": "price"}
        schema_bytes = json.dumps(contract, separators=(",", ":")).encode("utf-8")
        schema_sha256 = hashlib.sha256(schema_bytes).hexdigest()
        server = create_local_server(CarPredictionRuntime(contract=contract, bundle=bundle,
                                                          schema_sha256=schema_sha256,
                                                          schema_bytes=schema_bytes), 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            connection = HTTPConnection(host, port, timeout=3)
            connection.request("GET", "/api/schema", headers={"Origin": "http://127.0.0.1:8766"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Access-Control-Allow-Origin"), "http://127.0.0.1:8766")
            schema_body = response.read()
            self.assertEqual(response.getheader("X-Schema-SHA256"), hashlib.sha256(schema_body).hexdigest())
            self.assertEqual(response.getheader("Access-Control-Expose-Headers"), "X-Schema-SHA256")
            self.assertEqual(json.loads(schema_body)["case_id"], "synthetic-car")

            body = {"case_id": "synthetic-car", "model_id": "synthetic-model", "model_version": "synthetic-v1",
                    "inputs": {"mileage": 10, "make": "SYNTHETIC_A"}}
            connection.request("POST", "/api/predict", body=json.dumps(body), headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:8766"})
            response = connection.getresponse()
            result = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(result["prediction"], 20.0)

            body["model_id"] = "unavailable-model"
            connection.request("POST", "/api/predict", body=json.dumps(body), headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:8766"})
            response = connection.getresponse()
            result = json.loads(response.read())
            self.assertEqual(response.status, 404)
            self.assertEqual(result["error"]["code"], "model_not_available")

            connection.request("GET", "/api/schema", headers={"Origin": "https://attacker.invalid"})
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_json_rejects_duplicate_keys_and_nonfinite_constants(self):
        for payload in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    _decode_json(payload)

    def test_pinned_file_digest_is_enforced_before_use(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "schema.json"
            path.write_bytes(b"synthetic schema bytes")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(_read_regular_file(path, digest, "schema")[1], digest)
            with self.assertRaisesRegex(ValueError, "does not match"):
                _read_regular_file(path, "0" * 64, "schema")


if __name__ == "__main__":
    unittest.main()
