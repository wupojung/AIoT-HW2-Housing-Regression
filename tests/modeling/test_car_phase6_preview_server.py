from __future__ import annotations

import hashlib
import json
import socket
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

import numpy as np

from housing_regression.car_phase6_preview_server import create_preview_server, validate_tailnet_origin
from housing_regression.local_car_prediction_api import CarPredictionRuntime, create_local_server


class Transformer:
    def transform(self, frame):
        return np.asarray([[float(frame.iloc[0, 0]), 1.0]])


class Scaler:
    def transform(self, matrix):
        return matrix


class Estimator:
    def predict(self, matrix):
        return np.asarray([float(matrix[0, 0]) + 10.0])


def runtime():
    contract = {
        "schema_version": "0.1.0", "case_id": "synthetic-car", "model_id": "synthetic-model",
        "model_version": "synthetic-v1", "model_sha256": "a" * 64, "input_feature_count": 2,
        "input_features": [
            {"name": "mileage", "data_type": "number", "required": True, "nullable": False, "options": [], "unknown_category_behavior": None},
            {"name": "make", "data_type": "category", "required": True, "nullable": False,
             "options": [{"value": "MOCK_A"}], "unknown_category_behavior": "error"},
        ],
        "preprocessing_reference": {"raw_input_order": ["mileage", "make"]},
        "source_evidence": {"run_id": "synthetic-run", "configuration_id": "synthetic-config"},
    }
    schema_bytes = json.dumps(contract, separators=(",", ":")).encode()
    bundle = {"features": ["mileage", "make"], "transformer": Transformer(), "scaler": Scaler(),
              "mask": np.asarray([True, False]), "estimator": Estimator(), "target": "price"}
    return CarPredictionRuntime(contract=contract, bundle=bundle,
                                schema_sha256=hashlib.sha256(schema_bytes).hexdigest(), schema_bytes=schema_bytes)


class PreviewGatewayTests(unittest.TestCase):
    def test_tailnet_origin_requires_one_exact_https_ts_net_origin(self):
        self.assertEqual(validate_tailnet_origin("https://car-node.example.ts.net"), "https://car-node.example.ts.net")
        for value in ("http://car-node.example.ts.net", "https://*.ts.net", "https://car-node.ts.net/path", "https://example.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_tailnet_origin(value)

    def test_loopback_host_and_static_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text("synthetic preview", encoding="utf-8")
            (root / "app.js").write_text("// synthetic", encoding="utf-8")
            (root / "private.json").write_text("must not be served", encoding="utf-8")
            server = create_preview_server(root, api_port=19002, web_port=19001)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
                self.assertEqual(self.request(server.server_address[1], "GET", "/", host="127.0.0.1:19001")[0], 404)
                self.assertEqual(self.request(server.server_address[1], "GET", "/?car-phase6-prototype=1&car-local-inference=1", host="127.0.0.1:19001")[0], 200)
                self.assertEqual(self.request(server.server_address[1], "GET", "/private.json", host="127.0.0.1:19001")[0], 404)
                for private_path in ("/data/cases/car/package.json", "/local/run-03/model.joblib", "/private/final-model.joblib", "/docs/contracts/schemas/phase-06.json"):
                    with self.subTest(private_path=private_path):
                        self.assertEqual(self.request(server.server_address[1], "GET", private_path, host="127.0.0.1:19001")[0], 404)
                self.assertEqual(self.request(server.server_address[1], "GET", "/?unexpected=1", host="127.0.0.1:19001")[0], 404)
                self.assertEqual(self.request(server.server_address[1], "GET", "/", host="attacker.invalid")[0], 403)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_tailnet_host_is_exact_and_api_is_same_origin_proxy(self):
        tailnet = "https://car-node.example.ts.net"
        api = create_local_server(runtime(), 0, allowed_origins=["http://127.0.0.1:19011", tailnet])
        api_thread = threading.Thread(target=api.serve_forever, daemon=True)
        api_thread.start()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text("synthetic preview", encoding="utf-8")
            server = create_preview_server(root, api_port=api.server_address[1], web_port=19011, tailnet_origin=tailnet)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
                status, headers, body = self.request(server.server_address[1], "GET", "/api/schema", host="car-node.example.ts.net", origin=tailnet)
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("X-Schema-SHA256"), hashlib.sha256(body).hexdigest())
                self.assertEqual(json.loads(body)["case_id"], "synthetic-car")
                payload = {"case_id": "synthetic-car", "model_id": "synthetic-model", "model_version": "synthetic-v1",
                           "inputs": {"mileage": 42, "make": "MOCK_A"}}
                status, _, body = self.request(server.server_address[1], "POST", "/api/predict", host="car-node.example.ts.net", origin=tailnet, body=json.dumps(payload))
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["prediction"], 52.0)
                payload["model_version"] = "wrong-version"
                status, _, body = self.request(server.server_address[1], "POST", "/api/predict", host="car-node.example.ts.net", origin=tailnet, body=json.dumps(payload))
                self.assertEqual(status, 409)
                self.assertEqual(json.loads(body)["error"]["code"], "model_version_mismatch")
                self.assertEqual(self.request(server.server_address[1], "GET", "/api/schema", host="attacker.example.ts.net", origin=tailnet)[0], 403)
                self.assertEqual(self.request(server.server_address[1], "GET", "/api/schema", host="car-node.example.ts.net", origin="https://attacker.invalid")[0], 403)
                self.assertEqual(self.request(server.server_address[1], "GET", "/api/private-model", host="car-node.example.ts.net", origin=tailnet)[0], 404)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)
                api.shutdown(); api.server_close(); api_thread.join(timeout=2)

    def test_api_unavailable_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text("synthetic preview", encoding="utf-8")
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
            server = create_preview_server(root, api_port=port, web_port=19021)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, _, body = self.request(server.server_address[1], "GET", "/api/schema", host="127.0.0.1:19021")
                self.assertEqual(status, 503)
                self.assertEqual(json.loads(body)["error"]["code"], "local_api_unavailable")
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    @staticmethod
    def request(port, method, path, *, host, origin=None, body=None):
        connection = HTTPConnection("127.0.0.1", port, timeout=3)
        headers = {"Host": host}
        if origin is not None:
            headers["Origin"] = origin
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result


if __name__ == "__main__":
    unittest.main()
