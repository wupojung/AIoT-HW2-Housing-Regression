from __future__ import annotations

import hashlib
import base64
import json
import socket
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

import numpy as np

from housing_regression.car_phase6_preview_server import create_preview_server, validate_preview_bind_host
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


def write_test_site(root: Path):
    (root / "index.html").write_text("synthetic preview", encoding="utf-8")
    (root / "app.js").write_text("// synthetic", encoding="utf-8")
    data = root / "data"
    fixtures = data / "fixtures"
    fixtures.mkdir(parents=True)
    (fixtures / "car-single-small.json").write_text('{"fixture_status":"SYNTHETIC_UI_ONLY"}', encoding="utf-8")
    cases = []
    assets = {}
    for case_id, revision in (
        ("ames-full-model-exploration", "test-ames-r1"),
        ("used-car-price-optimized", "test-car-r1"),
    ):
        prefix = f"releases/{revision}/cases/{case_id}"
        asset_ref = "phases/phase-01/content.json"
        content = json.dumps({"case_id": case_id}, separators=(",", ":")).encode()
        asset_path = data / prefix / asset_ref
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_bytes(content)
        entry = {"path": asset_ref, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content), "mime": "application/json"}
        manifest = {"case_id": case_id, "package_revision": revision, "package_status": "PARTIAL", "files": [entry]}
        package_bytes = json.dumps(manifest, separators=(",", ":")).encode()
        package_path = data / prefix / "package.json"
        package_path.write_bytes(package_bytes)
        cases.append({"case_id": case_id, "package_ref": f"{prefix}/package.json", "package_status": "PARTIAL",
                      "package_sha256": hashlib.sha256(package_bytes).hexdigest(), "package_bytes": len(package_bytes)})
        assets[case_id] = (asset_path, prefix, asset_ref)
    index_bytes = json.dumps({"schema_version": "1.0.0", "release_id": "synthetic-release", "cases": cases}, separators=(",", ":")).encode()
    (data / "current-release.json").write_bytes(index_bytes)
    return assets


class PreviewGatewayTests(unittest.TestCase):
    def test_bind_allowlist_and_missing_tailscale_ip_fail_closed(self):
        self.assertEqual(validate_preview_bind_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(validate_preview_bind_host("100.64.0.1", {"100.64.0.1"}), "100.64.0.1")
        for value, addresses in (
            ("100.64.0.1", set()),
            ("192.168.1.20", {"192.168.1.20"}),
            ("0.0.0.0", {"0.0.0.0"}),
            ("::", {"::"}),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_preview_bind_host(value, addresses)

    def test_non_loopback_bind_requires_authentication_even_when_ip_is_present(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_test_site(root)
            with self.assertRaisesRegex(ValueError, "requires application authentication"):
                create_preview_server(root, api_port=19042, web_port=19041,
                                      bind_host="100.64.0.1", tailscale_ipv4_addresses={"100.64.0.1"})

    def test_loopback_host_and_static_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_test_site(root)
            (root / "private.json").write_text("must not be served", encoding="utf-8")
            server = create_preview_server(root, api_port=19002, web_port=19001)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
                self.assertEqual(self.request(server.server_address[1], "GET", "/", host="127.0.0.1:19001")[0], 200)
                self.assertEqual(self.request(server.server_address[1], "GET", "/?car-phase6-prototype=1&car-local-inference=1", host="127.0.0.1:19001")[0], 200)
                fixture_path = "/data/fixtures/car-single-small.json"
                self.assertEqual(self.request(server.server_address[1], "GET", fixture_path + "?car-phase6-prototype=1&car-local-inference=1", host="127.0.0.1:19001")[0], 200)
                self.assertEqual(self.request(server.server_address[1], "GET", "/private.json", host="127.0.0.1:19001")[0], 404)
                for private_path in ("/data/cases/car/package.json", "/local/run-03/model.joblib", "/private/final-model.joblib", "/docs/contracts/schemas/phase-06.json"):
                    with self.subTest(private_path=private_path):
                        self.assertEqual(self.request(server.server_address[1], "GET", private_path, host="127.0.0.1:19001")[0], 404)
                index_status, index_headers, index_body = self.request(server.server_address[1], "GET", "/data/current-release.json", host="127.0.0.1:19001")
                self.assertEqual(index_status, 200)
                self.assertEqual(index_headers.get("Content-Type"), "application/json")
                self.assertEqual(hashlib.sha256(index_body).hexdigest(), hashlib.sha256((root / "data/current-release.json").read_bytes()).hexdigest())
                package_url = "/data/releases/test-car-r1/cases/used-car-price-optimized/package.json"
                package_status, _, package_body = self.request(server.server_address[1], "GET", package_url, host="127.0.0.1:19001")
                self.assertEqual(package_status, 200)
                manifest = json.loads(package_body)
                public_asset = "/data/releases/test-car-r1/cases/used-car-price-optimized/phases/phase-01/content.json"
                asset_status, _, asset_body = self.request(server.server_address[1], "GET", public_asset, host="127.0.0.1:19001")
                self.assertEqual(asset_status, 200)
                self.assertEqual(hashlib.sha256(asset_body).hexdigest(), manifest["files"][0]["sha256"])
                self.assertEqual(self.request(server.server_address[1], "GET", public_asset + ".unlisted", host="127.0.0.1:19001")[0], 404)
                (root / "data/releases/test-car-r1/cases/used-car-price-optimized/phases/phase-01/content.json").write_text("changed", encoding="utf-8")
                self.assertEqual(self.request(server.server_address[1], "GET", public_asset, host="127.0.0.1:19001")[0], 502)
                self.assertEqual(self.request(server.server_address[1], "GET", "/?unexpected=1", host="127.0.0.1:19001")[0], 404)
                self.assertEqual(self.request(server.server_address[1], "GET", "/", host="attacker.invalid")[0], 403)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_authenticated_gateway_restricts_host_origin_and_api_routes(self):
        origin = "http://127.0.0.1:19011"
        token = "synthetic-auth-token-" + "x" * 40
        auth = "Basic " + base64.b64encode(f"regscope:{token}".encode()).decode("ascii")
        api = create_local_server(runtime(), 0, allowed_origins=[origin])
        api_thread = threading.Thread(target=api.serve_forever, daemon=True)
        api_thread.start()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_test_site(root)
            server = create_preview_server(root, api_port=api.server_address[1], web_port=19011, auth_token=token)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
                unauthenticated = self.request(server.server_address[1], "GET", "/", host="127.0.0.1:19011")
                self.assertEqual(unauthenticated[0], 401)
                self.assertIn("Basic", unauthenticated[1].get("WWW-Authenticate", ""))
                self.assertEqual(self.request(server.server_address[1], "GET", "/", host="127.0.0.1:19011", authorization="Basic wrong")[0], 401)
                self.assertEqual(self.request(server.server_address[1], "GET", "/", host="127.0.0.1:19011", authorization=auth)[0], 200)
                self.assertEqual(self.request(server.server_address[1], "GET", "/app.js", host="attacker.invalid", authorization=auth)[0], 403)
                self.assertEqual(self.request(server.server_address[1], "GET", "/?car-tailnet-preview=1&car-local-inference=1", host="127.0.0.1:19011", authorization=auth)[0], 403)
                self.assertEqual(self.request(server.server_address[1], "GET", "/data/fixtures/car-single-small.json", host="127.0.0.1:19011", authorization=auth)[0], 404)
                self.assertEqual(self.request(server.server_address[1], "GET", "/api/schema", host="127.0.0.1:19011", origin=origin)[0], 401)
                status, headers, body = self.request(server.server_address[1], "GET", "/api/schema", host="127.0.0.1:19011", origin=origin, authorization=auth)
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("X-Schema-SHA256"), hashlib.sha256(body).hexdigest())
                self.assertEqual(json.loads(body)["case_id"], "synthetic-car")
                status, _, health_body = self.request(server.server_address[1], "GET", "/api/health", host="127.0.0.1:19011", origin=origin, authorization=auth)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(health_body)["status"], "ready")
                payload = {"case_id": "synthetic-car", "model_id": "synthetic-model", "model_version": "synthetic-v1",
                           "inputs": {"mileage": 42, "make": "MOCK_A"}}
                status, _, body = self.request(server.server_address[1], "POST", "/api/predict", host="127.0.0.1:19011", origin="http://attacker.invalid", body=json.dumps(payload), authorization=auth)
                self.assertEqual(status, 403)
                status, _, _ = self.request(server.server_address[1], "POST", "/api/predict", host="127.0.0.1:19011", body=json.dumps(payload), authorization=auth)
                self.assertEqual(status, 403)
                status, _, body = self.request(server.server_address[1], "POST", "/api/predict", host="127.0.0.1:19011", origin=origin, body=json.dumps(payload), authorization=auth)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body)["prediction"], 52.0)
                payload["model_version"] = "wrong-version"
                status, _, body = self.request(server.server_address[1], "POST", "/api/predict", host="127.0.0.1:19011", origin=origin, body=json.dumps(payload), authorization=auth)
                self.assertEqual(status, 409)
                self.assertEqual(json.loads(body)["error"]["code"], "model_version_mismatch")
                self.assertEqual(self.request(server.server_address[1], "GET", "/api/schema", host="127.0.0.1:19011", origin="http://attacker.invalid", authorization=auth)[0], 403)
                self.assertEqual(self.request(server.server_address[1], "GET", "/api/private-model", host="127.0.0.1:19011", origin=origin, authorization=auth)[0], 404)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)
                api.shutdown(); api.server_close(); api_thread.join(timeout=2)

    def test_api_unavailable_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_test_site(root)
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

    def test_private_package_manifest_entry_prevents_gateway_startup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = write_test_site(root)
            _, package_root, _ = assets["used-car-price-optimized"]
            data_root = root / "data"
            package_path = data_root / package_root / "package.json"
            manifest = json.loads(package_path.read_text(encoding="utf-8"))
            private_bytes = b"synthetic-private-marker"
            manifest["files"].append({"path": "private/model-metadata.json", "sha256": hashlib.sha256(private_bytes).hexdigest(),
                                      "bytes": len(private_bytes), "mime": "application/json"})
            package_bytes = json.dumps(manifest, separators=(",", ":")).encode()
            package_path.write_bytes(package_bytes)
            index_path = data_root / "current-release.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            release_case = next(item for item in index["cases"] if item["case_id"] == "used-car-price-optimized")
            release_case["package_sha256"] = hashlib.sha256(package_bytes).hexdigest()
            release_case["package_bytes"] = len(package_bytes)
            index_path.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe or unsupported"):
                create_preview_server(root, api_port=19032, web_port=19031)

    @staticmethod
    def request(port, method, path, *, host, origin=None, body=None, authorization=None):
        connection = HTTPConnection("127.0.0.1", port, timeout=3)
        headers = {"Host": host}
        if origin is not None:
            headers["Origin"] = origin
        if authorization is not None:
            headers["Authorization"] = authorization
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result


if __name__ == "__main__":
    unittest.main()
