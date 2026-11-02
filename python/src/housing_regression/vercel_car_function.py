"""Protected, branch-scoped Vercel adapter for CAR Run 03 inference."""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from housing_regression.car_batch_prediction import (
    MAX_BATCH_REQUEST_BYTES,
    MAX_BATCH_RESPONSE_BYTES,
    predict_csv_batch,
)
from housing_regression.local_car_prediction_api import (
    MAX_REQUEST_BYTES,
    CAR_CASE_ID,
    CAR_MODEL_ID,
    CAR_MODEL_VERSION,
    PredictionApiError,
    _decode_json,
    load_verified_car_runtime,
)
from housing_regression.prediction_input_schema import PredictionInputSchemaError

_BRANCH = "feat/phase6-online-preview-delivery-20261102"
_PREVIEW_BRANCH_ALIAS = "regscope-git-feat-phase6-online-8ac39b-wupojung-8919s-projects.vercel.app"
_PRODUCTION_BRANCH = "deploy"
_PRODUCTION_ORIGIN = "https://regscope-aiot.vercel.app"
PRODUCTION_MAX_BATCH_ROWS = 10
_RUNTIME: Any | None = None
_LOGGER = logging.getLogger(__name__)


def _runtime_error_category(exc: Exception) -> str:
    """Return a fixed, non-sensitive category for private runtime diagnostics."""
    chain: list[Exception] = []
    current: Exception | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(chain) < 8:
        chain.append(current)
        seen.add(id(current))
        current = current.__cause__ or current.__context__

    for error in reversed(chain):
        if isinstance(error, (ModuleNotFoundError, ImportError)):
            return "import_error"
        if isinstance(error, FileNotFoundError):
            return "file_missing"
        if isinstance(error, PermissionError):
            return "permission_error"
        if isinstance(error, OSError):
            return "file_io_error"
        if isinstance(error, PredictionInputSchemaError):
            return "schema_or_asset_validation_error"
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return "invalid_asset_error"
    return "unexpected_error"


def _log_runtime_failure(stage: str, exc: Exception) -> None:
    allowed_stages = {"asset_decode", "ephemeral_asset_write", "model_contract_load"}
    safe_stage = stage if stage in allowed_stages else "runtime_initialization"
    _LOGGER.error(
        "car_runtime_initialization_failed stage=%s category=%s",
        safe_stage,
        _runtime_error_category(exc),
    )


def _preview_branch_allowed() -> bool:
    return (
        os.environ.get("VERCEL_ENV") == "preview"
        and os.environ.get("VERCEL_GIT_COMMIT_REF") == _BRANCH
    )


def _production_branch_allowed() -> bool:
    return (
        os.environ.get("VERCEL_ENV") == "production"
        and os.environ.get("VERCEL_GIT_COMMIT_REF") == _PRODUCTION_BRANCH
        and os.environ.get("REGSCOPE_CAR_PRODUCTION_INFERENCE") == "1"
    )


def _origin_is_authorized(origin: str | None, *, required: bool) -> bool:
    if not origin:
        return not required
    if _production_branch_allowed():
        return origin == _PRODUCTION_ORIGIN
    if not _preview_branch_allowed():
        return False
    expected_host = os.environ.get("VERCEL_URL", "")
    if not expected_host or "/" in expected_host:
        return False
    allowed_origins = {f"https://{expected_host}"}
    allowed_origins.add(f"https://{_PREVIEW_BRANCH_ALIAS}")
    return origin in allowed_origins


def _decode_assets() -> tuple[bytes, bytes, bytes]:
    encoded = os.environ.get("REGSCOPE_P6_CAR_RUN03_ASSETS_ZIP_B64")
    if not encoded:
        raise PredictionInputSchemaError("trusted Preview model assets are unavailable")
    if len(encoded) > 64 * 1024:
        raise PredictionInputSchemaError("trusted Preview asset archive exceeds the environment limit")
    try:
        archive_bytes = base64.b64decode(encoded, validate=True)
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            expected = {"final-model.joblib", "prediction-input-schema.json", "run-manifest.json"}
            infos = archive.infolist()
            if {item.filename for item in infos} != expected or len(infos) != len(expected):
                raise PredictionInputSchemaError("trusted Preview asset archive has unexpected files")
            limits = {
                "final-model.joblib": 1024 * 1024,
                "prediction-input-schema.json": 1024 * 1024,
                "run-manifest.json": 256 * 1024,
            }
            if any(item.file_size < 1 or item.file_size > limits[item.filename] for item in infos):
                raise PredictionInputSchemaError("trusted Preview asset archive exceeds a file limit")
            assets = {name: archive.read(name) for name in expected}
            return (
                assets["final-model.joblib"],
                assets["prediction-input-schema.json"],
                assets["run-manifest.json"],
            )
    except (ValueError, TypeError, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise PredictionInputSchemaError("trusted Preview model assets are malformed") from exc


def _runtime() -> Any:
    global _RUNTIME
    if not (_preview_branch_allowed() or _production_branch_allowed()):
        raise PermissionError("CAR inference is only available in its authorized Preview or Production branch")
    if _RUNTIME is not None:
        return _RUNTIME

    stage = "asset_decode"
    try:
        model, schema, manifest = _decode_assets()
        if not model or not schema or not manifest:
            raise PredictionInputSchemaError("trusted Preview model assets are empty")

        # The only disk copy is private ephemeral function storage. It is removed
        # immediately after the pinned loader hashes and deserializes the model.
        stage = "ephemeral_asset_write"
        with tempfile.TemporaryDirectory(prefix="regscope-car-") as temp_dir:
            root = Path(temp_dir)
            private = root / "private"
            private.mkdir(mode=0o700)
            (private / "final-model.joblib").write_bytes(model)
            (private / "run-manifest.json").write_bytes(manifest)
            schema_path = root / "prediction-input-schema.json"
            schema_path.write_bytes(schema)
            for path in (private / "final-model.joblib", private / "run-manifest.json", schema_path):
                path.chmod(0o600)
            stage = "model_contract_load"
            contract_schema = Path(__file__).resolve().parent / "prediction-input-schema-v0.1.schema.json"
            _RUNTIME = load_verified_car_runtime(root, schema_path, contract_schema_path=contract_schema)
    except Exception as exc:
        _log_runtime_failure(stage, exc)
        raise
    return _RUNTIME


def create_handler():
    class VercelCarHandler(BaseHTTPRequestHandler):
        server_version = "RegScopePreviewInference/1"
        sys_version = ""

        def log_message(self, _format: str, *args: Any) -> None:
            # Never write request paths, bodies, values, or exceptions to logs.
            return

        def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, document: Any) -> None:
            body = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            self._send(status, body)

        def _fail(self, status: int, code: str, message: str) -> None:
            self._send_json(status, {"error": {"code": code, "message": message}})

        def _origin_is_same_authorized_origin(self, *, required: bool) -> bool:
            return _origin_is_authorized(self.headers.get("Origin"), required=required)

        def _read_body(self, maximum: int) -> bytes | None:
            length = self.headers.get("Content-Length", "")
            if not length.isdigit():
                self._fail(400, "content_length_required", "請求長度無效。")
                return None
            size = int(length)
            if size < 1 or size > maximum:
                self._fail(413, "request_too_large", "請求內容大小不允許。")
                return None
            return self.rfile.read(size)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._fail(405, "method_not_allowed", "此同源端點不接受 OPTIONS。")

        def do_GET(self) -> None:  # noqa: N802
            route = urlsplit(self.path).path
            if route != "/api/schema":
                self._fail(404, "not_found", "找不到此 API 路徑。")
                return
            if not self._origin_is_same_authorized_origin(required=False):
                self._fail(403, "origin_rejected", "請求來源不允許。")
                return
            try:
                runtime = _runtime()
            except PermissionError:
                self._fail(404, "not_found", "找不到此 API 路徑。")
                return
            except Exception:
                self._fail(503, "model_unavailable", "受保護 Preview 的模型服務目前不可用。")
                return
            body = runtime.schema_bytes
            if len(body) > 64 * 1024:
                self._fail(503, "schema_unavailable", "輸入契約超過安全上限。")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Schema-SHA256", runtime.schema_sha256)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            route = urlsplit(self.path).path
            if route not in {"/api/predict", "/api/predict-batch"}:
                self._fail(404, "not_found", "找不到此 API 路徑。")
                return
            if not self._origin_is_same_authorized_origin(required=True):
                self._fail(403, "origin_rejected", "請求來源不允許。")
                return
            is_batch = route == "/api/predict-batch"
            expected_type = "text/csv" if is_batch else "application/json"
            if self.headers.get_content_type() != expected_type:
                self._fail(415, "content_type_required", "請求內容類型不符合此端點要求。")
                return
            try:
                runtime = _runtime()
            except PermissionError:
                self._fail(404, "not_found", "找不到此 API 路徑。")
                return
            except Exception:
                self._fail(503, "model_unavailable", "受保護 Preview 的模型服務目前不可用。")
                return
            payload = self._read_body(MAX_BATCH_REQUEST_BYTES if is_batch else MAX_REQUEST_BYTES)
            if payload is None:
                return
            try:
                if is_batch:
                    batch_row_limit = (
                        PRODUCTION_MAX_BATCH_ROWS
                        if _production_branch_allowed()
                        else None
                    )
                    if batch_row_limit is None:
                        result = predict_csv_batch(runtime, payload)
                    else:
                        result = predict_csv_batch(runtime, payload, max_rows=batch_row_limit)
                    body = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
                    if len(body) > MAX_BATCH_RESPONSE_BYTES:
                        raise PredictionApiError("batch_response_too_large", "批次結果超過安全回應上限。", 413)
                    self._send(200, body)
                    return
                request = _decode_json(payload)
                if not isinstance(request, dict) or set(request) != {"case_id", "model_id", "model_version", "inputs"}:
                    raise PredictionApiError("invalid_request", "請求只能包含案例、模型版本與一筆輸入。", 400)
                if request["case_id"] != CAR_CASE_ID or request["model_id"] != CAR_MODEL_ID:
                    raise PredictionApiError("model_not_available", "指定的案例或模型目前不可用。", 404)
                if request["model_version"] != CAR_MODEL_VERSION:
                    raise PredictionApiError("model_version_mismatch", "指定模型版本與目前載入模型不一致。", 409)
                self._send_json(200, runtime.predict(request["inputs"]))
            except PredictionApiError as exc:
                self._send_json(exc.status, {"error": {"code": exc.code, "message": str(exc), "fields": exc.fields}})
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                self._fail(400, "invalid_json", "請求不是有效 JSON，或包含重複欄位／非有限數字。")
            except Exception:
                self._fail(500, "inference_failed", "模型無法處理此請求；未顯示輸入或模型資訊。")

    return VercelCarHandler
