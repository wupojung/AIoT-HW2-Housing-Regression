"""Loopback-only prediction adapter for the verified CAR Run 03 Final Fit.

This is a local research experiment endpoint, not a deployable service. It
accepts only a complete raw-input record and never accepts artifact paths or
model uploads from a request.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

import numpy as np
import pandas as pd

from housing_regression.contracts import ContractValidationError, validate_document
from housing_regression.prediction_input_schema import PredictionInputSchemaError, prediction_input_schema_path

MAX_REQUEST_BYTES = 64 * 1024
LOCAL_WEB_ORIGIN = "http://127.0.0.1:8766"
CAR_CASE_ID = "used-car-price-optimized"
CAR_MODEL_ID = "used-car-price-optimized-car-mutual-information-8b59f9573a65"
CAR_MODEL_VERSION = "83caf79b21b8"
CAR_RUN_ID = "used-car-e2e-20261028-03"
CAR_CONFIGURATION_ID = "car-mutual-information-8b59f9573a65"
CAR_MODEL_SHA256 = "1dcf99781afa53cbdf09163b210b991eecc982b961d1a33d8265528f0a19099d"
CAR_SCHEMA_SHA256 = "4fcb528328903e54fe39a214be682d437db26c2cd9655971a486170d513d881a"


class PredictionApiError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422, fields: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.fields = fields or []


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON property")
        result[key] = value
    return result


def _decode_json(payload: bytes) -> Any:
    return json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def _read_regular_file(path: Path, expected_sha256: str, label: str) -> tuple[bytes, str]:
    """Hash and return bytes from one verified file descriptor; reject symlinks."""
    expected = expected_sha256.lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise PredictionInputSchemaError(f"{label} expected digest is invalid")
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            named = path.lstat()
            if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(opened, named):
                raise PredictionInputSchemaError(f"{label} must be a regular non-symlink file")
            digest = hashlib.sha256()
            chunks: list[bytes] = []
            while block := stream.read(1024 * 1024):
                digest.update(block)
                chunks.append(block)
            actual = digest.hexdigest()
            if actual != expected:
                raise PredictionInputSchemaError(f"{label} SHA-256 does not match the pinned digest")
            return b"".join(chunks), actual
    except OSError as exc:
        raise PredictionInputSchemaError(f"could not read verified {label}") from exc


def _read_local_json(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            named = path.lstat()
            if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(opened, named):
                raise PredictionInputSchemaError(f"{label} must be a regular non-symlink file")
            value = _decode_json(stream.read())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, PredictionInputSchemaError):
            raise
        raise PredictionInputSchemaError(f"could not read {label} JSON") from exc
    if not isinstance(value, dict):
        raise PredictionInputSchemaError(f"{label} JSON root must be an object")
    return value


def _safe_model_path(run_root: Path, manifest: Mapping[str, Any]) -> Path:
    relative = manifest.get("model_artifact_private_path")
    if not isinstance(relative, str):
        raise PredictionInputSchemaError("Run manifest does not identify its private model artifact")
    ref = PurePosixPath(relative)
    if ref.is_absolute() or ".." in ref.parts or "\\" in relative or ref.as_posix() != "private/final-model.joblib":
        raise PredictionInputSchemaError("Run manifest model reference is not the expected CAR Final Fit artifact")
    root = run_root.resolve(strict=True)
    if run_root.is_symlink():
        raise PredictionInputSchemaError("Run root must not be a symlink")
    private_dir = root / "private"
    model_path = root.joinpath(*ref.parts)
    if private_dir.is_symlink() or model_path.is_symlink() or not model_path.is_file():
        raise PredictionInputSchemaError("trusted CAR Final Fit artifact is missing or unsafe")
    if not model_path.resolve(strict=True).is_relative_to(root):
        raise PredictionInputSchemaError("model artifact escapes the verified Run root")
    return model_path


def load_verified_car_runtime(run_root: Path, schema_path: Path) -> "CarPredictionRuntime":
    """Load only the pinned CAR model/schema after binding both to Run 03."""
    schema_bytes, _ = _read_regular_file(schema_path, CAR_SCHEMA_SHA256, "input schema")
    manifest_path = run_root / "private" / "run-manifest.json"
    manifest = _read_local_json(manifest_path, "Run manifest")
    try:
        contract = _decode_json(schema_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PredictionInputSchemaError("verified input schema is not valid JSON") from exc
    if not isinstance(contract, dict):
        raise PredictionInputSchemaError("input schema root must be an object")

    try:
        validate_document(contract, prediction_input_schema_path())
    except ContractValidationError as exc:
        raise PredictionInputSchemaError("verified input schema fails the v0.1 contract") from exc

    identity = (contract.get("case_id"), contract.get("model_id"), contract.get("model_version"), contract.get("model_sha256"))
    expected_identity = (CAR_CASE_ID, CAR_MODEL_ID, CAR_MODEL_VERSION, CAR_MODEL_SHA256)
    if identity != expected_identity:
        raise PredictionInputSchemaError("input schema does not identify the pinned CAR model")
    evidence = contract.get("source_evidence") or {}
    integrity = manifest.get("integrity") or {}
    if (
        manifest.get("case_id") != CAR_CASE_ID
        or manifest.get("run_id") != CAR_RUN_ID
        or evidence.get("run_id") != CAR_RUN_ID
        or evidence.get("configuration_id") != CAR_CONFIGURATION_ID
        or evidence.get("source_data_sha256") != manifest.get("source_data_sha256")
        or evidence.get("source_data_sha256") != integrity.get("source_sha256")
        or evidence.get("config_sha256") != integrity.get("config_sha256")
        or evidence.get("code_sha256") != manifest.get("code_sha256")
        or integrity.get("run_id") != CAR_RUN_ID
        or integrity.get("final_model_sha256") != CAR_MODEL_SHA256
    ):
        raise PredictionInputSchemaError("Run manifest and input schema identity do not match")

    model_path = _safe_model_path(run_root, manifest)
    # The existing exporter uses one-open/hash-then-deserialize, so replacement
    # of the path after verification cannot change the bytes loaded by joblib.
    from tools.modeling.export_prediction_input_schema import _load_verified_bundle

    bundle, model_sha = _load_verified_bundle(model_path, CAR_MODEL_SHA256)
    if (
        model_sha != contract["model_sha256"]
        or bundle.get("run_id") != CAR_RUN_ID
        or bundle.get("configuration_id") != CAR_CONFIGURATION_ID
        or bundle.get("source_sha256") != evidence.get("source_data_sha256")
        or bundle.get("target") != "price"
        or bundle.get("features") != contract.get("preprocessing_reference", {}).get("raw_input_order")
    ):
        raise PredictionInputSchemaError("verified model bundle does not match its Run 03 input contract")
    if not hasattr(bundle.get("transformer"), "transform") or not hasattr(bundle.get("scaler"), "transform") or not hasattr(bundle.get("estimator"), "predict"):
        raise PredictionInputSchemaError("verified model bundle lacks the fitted inference steps")
    mask = np.asarray(bundle.get("mask"))
    selected_count = contract.get("preprocessing_reference", {}).get("selected_encoded_feature_count")
    if mask.ndim != 1 or mask.dtype.kind != "b" or int(mask.sum()) != selected_count:
        raise PredictionInputSchemaError("verified model selection mask does not match the input contract")
    features = contract.get("input_features")
    if not isinstance(features, list) or len(features) != 15 or contract.get("input_feature_count") != 15:
        raise PredictionInputSchemaError("pinned CAR Runtime Input contract is incomplete")
    runtime_names = [field.get("name") for field in features]
    if runtime_names != bundle["features"] or len(set(runtime_names)) != len(runtime_names):
        raise PredictionInputSchemaError("CAR input feature order does not match the fitted transformer")
    return CarPredictionRuntime(
        contract=contract,
        bundle=bundle,
        schema_sha256=hashlib.sha256(schema_bytes).hexdigest(),
        schema_bytes=schema_bytes,
    )


def validate_inputs(contract: Mapping[str, Any], inputs: Any) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise PredictionApiError("invalid_inputs", "輸入資料必須是欄位名稱與值組成的物件。")
    fields = contract.get("input_features")
    if not isinstance(fields, list) or not fields:
        raise PredictionApiError("schema_unavailable", "模型輸入契約不可用。", 503)
    by_name = {field["name"]: field for field in fields}
    expected_names = list(by_name)
    actual_names = set(inputs)
    missing = [name for name in expected_names if name not in actual_names]
    extra = sorted(actual_names - set(expected_names))
    if missing or extra:
        raise PredictionApiError(
            "field_set_mismatch",
            "請提供契約要求的完整欄位，且不要加入額外欄位。",
            fields=missing + extra,
        )

    normalized: dict[str, Any] = {}
    for field in fields:
        name = field["name"]
        value = inputs[name]
        if value is None:
            if field.get("nullable") is not True:
                raise PredictionApiError("null_not_supported", "此欄位的 JSON null 處理方式未獲證據確認。", fields=[name])
            normalized[name] = None
            continue
        data_type = field.get("data_type")
        if data_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise PredictionApiError("invalid_number", "數值欄位必須是有限的 JSON 數字。", fields=[name])
            if name == "year" and value <= 0:
                raise PredictionApiError("invalid_domain_value", "年份必須大於 0；目前未設定上限。", fields=[name])
            if name == "odometer" and value < 0:
                raise PredictionApiError("invalid_domain_value", "里程數不可為負數；單位與合理範圍未確認。", fields=[name])
            if name == "image_count" and value < 0:
                raise PredictionApiError("invalid_domain_value", "圖片數量不可為負數；0 可接受。", fields=[name])
            normalized[name] = value
            continue
        if data_type != "category" or not isinstance(value, str):
            raise PredictionApiError("invalid_type", "類別欄位必須是字串。", fields=[name])
        options = field.get("options")
        if not isinstance(options, list) or not options:
            raise PredictionApiError("category_metadata_unavailable", "此類別欄位缺少已驗證的 Encoder 類別資訊。", 503, [name])
        training_values = {option.get("value") for option in options if isinstance(option, dict)}
        unknown_behavior = field.get("unknown_category_behavior")
        if value not in training_values and unknown_behavior == "error":
            raise PredictionApiError("unknown_category", "此類別不在已擬合 Encoder 的類別中。", fields=[name])
        if value not in training_values and unknown_behavior not in {"ignore", "infrequent_if_exist", "warn"}:
            raise PredictionApiError("unknown_category_behavior_unverified", "未知類別的模型處理方式未獲證據確認。", 503, [name])
        normalized[name] = value
    return normalized


class CarPredictionRuntime:
    def __init__(
        self,
        *,
        contract: Mapping[str, Any],
        bundle: Mapping[str, Any],
        schema_sha256: str | None = None,
        schema_bytes: bytes | None = None,
    ):
        self.contract = contract
        self.bundle = bundle
        self.schema_sha256 = schema_sha256
        self.schema_bytes = schema_bytes

    def predict(self, inputs: Any) -> dict[str, Any]:
        values = validate_inputs(self.contract, inputs)
        columns = list(self.contract["preprocessing_reference"]["raw_input_order"])
        frame = pd.DataFrame([[values[name] for name in columns]], columns=columns)
        try:
            encoded = self.bundle["transformer"].transform(frame)
            scaled = self.bundle["scaler"].transform(encoded)
            selected = scaled[:, np.asarray(self.bundle["mask"], dtype=bool)]
            prediction = np.asarray(self.bundle["estimator"].predict(selected), dtype=float).reshape(-1)
        except Exception as exc:
            # Never echo request values or model internals in API errors.
            raise PredictionApiError("inference_failed", "模型無法處理這筆輸入；請檢查欄位格式與類別值。", 422) from exc
        if prediction.size != 1 or not math.isfinite(float(prediction[0])):
            raise PredictionApiError("invalid_model_output", "模型未產生有限的單筆數值結果。", 500)
        return {
            "case_id": self.contract["case_id"],
            "model_id": self.contract["model_id"],
            "model_version": self.contract["model_version"],
            "run_id": self.contract["source_evidence"]["run_id"],
            "configuration_id": self.contract["source_evidence"]["configuration_id"],
            "target": self.bundle["target"],
            "prediction": float(prediction[0]),
            "unit": None,
            "research_quality_note": "本機真實模型推論；模型品質仍受既有負 R² 與低於 Dummy Baseline 的限制。",
        }


def _validate_allowed_origins(origins: Iterable[str]) -> frozenset[str]:
    checked: set[str] = set()
    for origin in origins:
        if not isinstance(origin, str):
            raise ValueError("allowed API origins must be exact origin strings")
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or origin.endswith("/")
            or "*" in origin
        ):
            raise ValueError("allowed API origins must be exact HTTP(S) origins without paths")
        if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("non-loopback API origins must use HTTPS")
        checked.add(origin)
    if not checked:
        raise ValueError("at least one exact API origin is required")
    return frozenset(checked)


def make_handler(
    runtime: CarPredictionRuntime,
    *,
    allowed_origin: str = LOCAL_WEB_ORIGIN,
    allowed_origins: Iterable[str] | None = None,
):
    origins = _validate_allowed_origins(allowed_origins if allowed_origins is not None else [allowed_origin])

    def cors_origin(request_origin: str | None) -> str | None:
        return request_origin if request_origin in origins else None

    class LocalPredictionHandler(BaseHTTPRequestHandler):
        server_version = "RegScopeLocalPrediction/1"
        sys_version = ""

        def log_message(self, _format: str, *args: Any) -> None:
            # Request bodies and URLs are deliberately not written to logs.
            return

        def _send(self, status: int, document: Mapping[str, Any], *, cors: str | None = None) -> None:
            payload = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Vary", "Origin")
            if cors:
                self.send_header("Access-Control-Allow-Origin", cors)
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Max-Age", "300")
            self.end_headers()
            self.wfile.write(payload)

        def _send_schema(self, *, cors: str | None = None) -> None:
            payload = runtime.schema_bytes
            digest = runtime.schema_sha256
            if not isinstance(payload, bytes) or not isinstance(digest, str):
                self._send(503, {"error": {"code": "schema_unavailable", "message": "已驗證的輸入契約目前不可用。"}}, cors=cors)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Schema-SHA256", digest)
            self.send_header("Vary", "Origin")
            if cors:
                self.send_header("Access-Control-Allow-Origin", cors)
                self.send_header("Access-Control-Expose-Headers", "X-Schema-SHA256")
            self.end_headers()
            self.wfile.write(payload)

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            return origin is None or origin in origins

        def do_OPTIONS(self) -> None:  # noqa: N802
            if urlsplit(self.path).path not in {"/api/predict", "/api/predict-batch"} or not self.headers.get("Origin") or not self._origin_allowed():
                self._send(403, {"error": {"code": "origin_or_route_rejected", "message": "請求來源或路徑不允許。"}})
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin"))
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "300")
            self.send_header("Vary", "Origin")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            route = urlsplit(self.path).path
            if route not in {"/health", "/api/schema"}:
                self._send(404, {"error": {"code": "not_found", "message": "找不到此 API 路徑。"}})
                return
            if not self._origin_allowed():
                self._send(403, {"error": {"code": "origin_rejected", "message": "請求來源不允許。"}})
                return
            if route == "/health":
                document = {"status": "ready", "case_id": runtime.contract["case_id"], "model_id": runtime.contract["model_id"], "model_version": runtime.contract["model_version"], "run_id": runtime.contract["source_evidence"]["run_id"], "configuration_id": runtime.contract["source_evidence"]["configuration_id"], "mode": "LOCAL_EXPERIMENT"}
            else:
                self._send_schema(cors=cors_origin(self.headers.get("Origin")))
                return
            self._send(200, document, cors=cors_origin(self.headers.get("Origin")))

        def do_POST(self) -> None:  # noqa: N802
            route = urlsplit(self.path).path
            if route not in {"/api/predict", "/api/predict-batch"}:
                self._send(404, {"error": {"code": "not_found", "message": "找不到此 API 路徑。"}})
                return
            if not self._origin_allowed():
                self._send(403, {"error": {"code": "origin_rejected", "message": "請求來源不允許。"}})
                return
            is_batch = route == "/api/predict-batch"
            expected_content_type = "text/csv" if is_batch else "application/json"
            if self.headers.get_content_type() != expected_content_type:
                message = "請使用 text/csv。" if is_batch else "請使用 application/json。"
                self._send(415, {"error": {"code": "content_type_required", "message": message}})
                return
            length_text = self.headers.get("Content-Length")
            if length_text is None or not length_text.isdigit():
                self._send(400, {"error": {"code": "content_length_required", "message": "請求長度無效。"}})
                return
            length = int(length_text)
            if is_batch:
                from housing_regression.car_batch_prediction import MAX_BATCH_REQUEST_BYTES, predict_csv_batch

                max_bytes = MAX_BATCH_REQUEST_BYTES
            else:
                max_bytes = MAX_REQUEST_BYTES
            if length < 1 or length > max_bytes:
                self._send(413, {"error": {"code": "request_too_large", "message": "請求內容大小不允許。"}})
                return
            payload = self.rfile.read(length)
            if is_batch:
                try:
                    result = predict_csv_batch(runtime, payload)
                except PredictionApiError as exc:
                    self._send(exc.status, {"error": {"code": exc.code, "message": str(exc), "fields": exc.fields}}, cors=cors_origin(self.headers.get("Origin")))
                    return
                self._send(200, result, cors=cors_origin(self.headers.get("Origin")))
                return
            try:
                request = _decode_json(payload)
                if not isinstance(request, dict) or set(request) != {"case_id", "model_id", "model_version", "inputs"}:
                    raise PredictionApiError("invalid_request", "請求只能包含案例、模型版本與一筆輸入。", 400)
                if request["case_id"] != runtime.contract["case_id"] or request["model_id"] != runtime.contract["model_id"]:
                    raise PredictionApiError("model_not_available", "指定的案例或模型目前不可用。", 404)
                if request["model_version"] != runtime.contract["model_version"]:
                    raise PredictionApiError("model_version_mismatch", "指定模型版本與本機載入模型不一致。", 409)
                result = runtime.predict(request["inputs"])
            except PredictionApiError as exc:
                self._send(exc.status, {"error": {"code": exc.code, "message": str(exc), "fields": exc.fields}}, cors=cors_origin(self.headers.get("Origin")))
                return
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                self._send(400, {"error": {"code": "invalid_json", "message": "請求不是有效 JSON，或包含重複欄位／非有限數字。"}}, cors=cors_origin(self.headers.get("Origin")))
                return
            self._send(200, result, cors=cors_origin(self.headers.get("Origin")))

    return LocalPredictionHandler


def create_local_server(
    runtime: CarPredictionRuntime,
    port: int = 8767,
    *,
    allowed_origins: Iterable[str] | None = None,
) -> HTTPServer:
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("local API port must be between 0 and 65535")
    handler = make_handler(runtime, allowed_origins=allowed_origins) if allowed_origins is not None else make_handler(runtime)
    return HTTPServer(("127.0.0.1", port), handler)
