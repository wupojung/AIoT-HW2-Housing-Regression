"""Fail-closed Vercel adapter for the pinned Steam Review Multiplier model."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .steam_model_compat import CASE_ID, MODEL_INPUT_FIELDS
from .steam_review_multiplier import log_to_k


MODEL_ID = "steam-review-multiplier-random-forest"
MODEL_VERSION = "1.0.0"
RUN_ID = "steam-review-multiplier-run-01"
CONFIGURATION_ID = "random_forest-all"
MODEL_SHA256 = "228ad27ea48cfe53652cbf0f33141445bdc045047ad55c02689ee5da0f63ac53"
SCHEMA_RELATIVE_PATH = Path(
    "web/data/releases/steam-homework-20261102-02/cases/steam-review-multiplier/"
    "phases/phase-06/input-schema.json"
)
SCHEMA_SHA256 = "b7135570418ed2c1a0d96f32ed906e894da58a0f7148f3e1d6c5eb2a494293bc"
MODEL_BLOB_PATH = f"steam/run-01/{MODEL_SHA256}/steam-review-multiplier.joblib"
MAX_MODEL_BYTES = 32 * 1024 * 1024
MAX_SCHEMA_BYTES = 64 * 1024
MAX_SINGLE_REQUEST_BYTES = 32 * 1024
MAX_BATCH_REQUEST_BYTES = 1024 * 1024
MAX_BATCH_ROWS = 10
MAX_BATCH_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REVIEW_COUNT = 10_000_000

_BOOL_FIELDS = frozenset({
    "windows", "mac", "linux", "has_english", "has_traditional_chinese", "has_website",
})
_INTEGER_FIELDS = frozenset({
    "required_age", "dlc_count", "achievements", "release_year", "genre_count",
    "category_count", "tag_count", "supported_language_count", "full_audio_language_count",
    "developer_count", "publisher_count", "screenshot_count", "movie_count",
})
_COUNT_FIELDS = _INTEGER_FIELDS - {"release_year"}
_NUMERIC_FIELDS = frozenset(MODEL_INPUT_FIELDS) - {"genres"} - _BOOL_FIELDS
_PRODUCTION_ORIGIN = "https://regscope-aiot.vercel.app"
_PREVIEW_BRANCH = "feat/steam-phase6-online-prediction-20261102"
_PRODUCTION_BRANCH = "deploy"
_RUNTIME: "SteamPredictionRuntime | None" = None


class SteamPredictionError(ValueError):
    def __init__(self, code: str, message: str, status: int = 400, field: str | None = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.field = field


def deployment_is_enabled() -> bool:
    if os.environ.get("VERCEL_ENV") == "preview":
        return os.environ.get("VERCEL_GIT_COMMIT_REF") == _PREVIEW_BRANCH
    return (
        os.environ.get("VERCEL_ENV") == "production"
        and os.environ.get("VERCEL_GIT_COMMIT_REF") == _PRODUCTION_BRANCH
        and os.environ.get("REGSCOPE_STEAM_PRODUCTION_INFERENCE") == "1"
    )


def authorized_host(host: str | None) -> bool:
    if not host:
        return False
    if os.environ.get("VERCEL_ENV") == "production":
        return deployment_is_enabled() and host.lower() in {
            "regscope-aiot.vercel.app", "regscope-aiot.vercel.app:443",
        }
    if not deployment_is_enabled():
        return False
    expected = os.environ.get("VERCEL_URL", "").lower()
    return bool(expected and host.lower() == expected)


def authorized_origin(origin: str | None) -> bool:
    if not origin:
        return False
    if os.environ.get("VERCEL_ENV") == "production":
        return deployment_is_enabled() and origin == _PRODUCTION_ORIGIN
    expected = os.environ.get("VERCEL_URL", "").lower()
    return bool(deployment_is_enabled() and expected and origin == f"https://{expected}")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_schema_bytes() -> bytes:
    path = _project_root() / SCHEMA_RELATIVE_PATH
    payload = path.read_bytes()
    if len(payload) < 1 or len(payload) > MAX_SCHEMA_BYTES:
        raise RuntimeError("schema size rejected")
    if hashlib.sha256(payload).hexdigest() != SCHEMA_SHA256:
        raise RuntimeError("schema digest rejected")
    schema = json.loads(payload)
    if schema.get("case_id") != CASE_ID or schema.get("model_version") != MODEL_VERSION:
        raise RuntimeError("schema identity rejected")
    if tuple(schema.get("input_fields", ())) != tuple(MODEL_INPUT_FIELDS):
        raise RuntimeError("schema input order rejected")
    if set(schema.get("required", ())) != set(MODEL_INPUT_FIELDS) | {"review_count"}:
        raise RuntimeError("schema required fields rejected")
    if not isinstance(schema.get("genre_options"), list) or not schema["genre_options"]:
        raise RuntimeError("schema genre choices rejected")
    return payload


def _read_private_model_bytes(opener=urllib.request.urlopen) -> bytes:
    store_id = os.environ.get("BLOB_STORE_ID", "")
    oidc_token = os.environ.get("VERCEL_OIDC_TOKEN", "")
    if not re.fullmatch(r"store_[A-Za-z0-9]+", store_id) or not oidc_token:
        raise RuntimeError("private model storage unavailable")
    request = urllib.request.Request(
        f"https://{store_id}.private.blob.vercel-storage.com/{MODEL_BLOB_PATH}",
        headers={"Authorization": f"Bearer {oidc_token}", "Accept": "application/octet-stream"},
        method="GET",
    )
    with opener(request, timeout=8) as response:
        if getattr(response, "status", 200) != 200:
            raise RuntimeError("private model fetch rejected")
        payload = response.read(MAX_MODEL_BYTES + 1)
    if not payload or len(payload) > MAX_MODEL_BYTES:
        raise RuntimeError("private model size rejected")
    if hashlib.sha256(payload).hexdigest() != MODEL_SHA256:
        raise RuntimeError("private model digest rejected")
    return payload


@dataclass
class SteamPredictionRuntime:
    model: Any
    schema: dict[str, Any]
    schema_bytes: bytes
    schema_sha256: str = SCHEMA_SHA256
    model_sha256: str = MODEL_SHA256

    @property
    def identity(self) -> dict[str, str]:
        return {
            "case_id": CASE_ID,
            "model_id": MODEL_ID,
            "model_version": MODEL_VERSION,
            "run_id": RUN_ID,
            "configuration_id": CONFIGURATION_ID,
            "model_sha256": self.model_sha256,
            "schema_sha256": self.schema_sha256,
            "target": "K midpoint proxy",
            "target_unit": "K multiplier",
        }

    def predict(self, inputs: dict[str, Any], review_count: Any) -> dict[str, Any]:
        normalized = validate_inputs(inputs, review_count, self.schema)
        row = {field: normalized[field] for field in MODEL_INPUT_FIELDS}
        frame = pd.DataFrame([{**row, "genres": list(row["genres"])}])
        predicted_k = float(log_to_k(self.model.predict(frame))[0])
        if not math.isfinite(predicted_k) or not 0 <= predicted_k < 10_000_000:
            raise SteamPredictionError("prediction_out_of_range", "模型輸出超出可回傳範圍。", 500)
        count = normalized["review_count"]
        return {
            **self.identity,
            "predicted_k": predicted_k,
            "review_count": count,
            "estimated_ownership": predicted_k * count,
            "fixed_k_30_ownership": 30.0 * count,
        }


def log_to_k(values: Any) -> np.ndarray:
    return np.maximum(0.0, np.expm1(np.asarray(values, dtype=float)))


def validate_inputs(inputs: Any, review_count: Any, schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise SteamPredictionError("invalid_inputs", "features 必須是物件。", field="features")
    expected = set(MODEL_INPUT_FIELDS)
    missing = expected - set(inputs)
    extra = set(inputs) - expected
    if missing or extra:
        raise SteamPredictionError("invalid_fields", "輸入欄位與 Steam 模型契約不符。", field="features")
    result: dict[str, Any] = {}
    options = set(schema["genre_options"])
    genres = inputs.get("genres")
    if not isinstance(genres, list) or any(not isinstance(item, str) or item not in options for item in genres):
        raise SteamPredictionError("invalid_category", "genres 必須全部來自契約列出的選項。", field="genres")
    result["genres"] = list(dict.fromkeys(genres))
    for field in _BOOL_FIELDS:
        value = inputs[field]
        if value not in (True, False, 0, 1) or isinstance(value, str):
            raise SteamPredictionError("invalid_boolean", "布林欄位只能使用 true 或 false。", field=field)
        result[field] = bool(value)
    for field in _NUMERIC_FIELDS:
        value = inputs[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise SteamPredictionError("invalid_number", "數值欄位必須是有限數字。", field=field)
        number = float(value)
        if abs(number) >= 1_000_000:
            raise SteamPredictionError("invalid_number", "數值超出服務技術上限。", field=field)
        if field in _COUNT_FIELDS and (number < 0 or not number.is_integer()):
            raise SteamPredictionError("invalid_number", "數量欄位必須是非負整數。", field=field)
        if field == "price" and not schema["limits"]["price_min"] <= number <= schema["limits"]["price_max"]:
            raise SteamPredictionError("invalid_number", "price 超出契約範圍。", field=field)
        if field == "release_year":
            bounds = schema["limits"]
            if not number.is_integer() or not bounds["release_year_min"] <= number <= bounds["release_year_max"]:
                raise SteamPredictionError("invalid_number", "release_year 超出契約範圍。", field=field)
        result[field] = number
    if isinstance(review_count, bool) or not isinstance(review_count, (int, float)):
        raise SteamPredictionError("invalid_number", "review_count 必須是正整數。", field="review_count")
    count = float(review_count)
    bounds = schema["limits"]
    if not count.is_integer() or not bounds["review_count_min"] <= count <= min(bounds["review_count_max"], MAX_REVIEW_COUNT):
        raise SteamPredictionError("invalid_number", "review_count 超出契約範圍。", field="review_count")
    result["review_count"] = int(count)
    return result


def load_runtime() -> SteamPredictionRuntime:
    global _RUNTIME
    if not deployment_is_enabled():
        raise PermissionError("Steam inference is disabled for this deployment")
    if _RUNTIME is not None:
        return _RUNTIME
    schema_bytes = load_schema_bytes()
    model_bytes = _read_private_model_bytes()
    model = joblib.load(io.BytesIO(model_bytes))
    steps = getattr(model, "named_steps", {})
    if tuple(steps) != ("encode", "impute", "scale", "model"):
        raise RuntimeError("model pipeline contract rejected")
    if not hasattr(steps["encode"], "genre_vocabulary_") or not hasattr(steps["model"], "estimators_"):
        raise RuntimeError("model identity rejected")
    schema = json.loads(schema_bytes)
    _RUNTIME = SteamPredictionRuntime(model=model, schema=schema, schema_bytes=schema_bytes)
    return _RUNTIME


def public_schema(runtime: SteamPredictionRuntime) -> dict[str, Any]:
    return {
        **runtime.identity,
        "input_schema": runtime.schema,
        "max_batch_rows": MAX_BATCH_ROWS,
        "max_batch_request_bytes": MAX_BATCH_REQUEST_BYTES,
    }


def _genres_from_csv(value: str, options: set[str]) -> list[str]:
    text = value.strip()
    if text.startswith("["):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("invalid_genres")
        genres = parsed
    elif not text:
        genres = []
    else:
        genres = [part.strip() for part in text.split("|") if part.strip()]
    if any(not isinstance(item, str) or item not in options for item in genres):
        raise ValueError("invalid_category")
    return list(dict.fromkeys(genres))


def predict_csv_batch(runtime: SteamPredictionRuntime, payload: bytes) -> dict[str, Any]:
    if not payload or len(payload) > MAX_BATCH_REQUEST_BYTES:
        raise SteamPredictionError("request_too_large", "CSV 檔案為空或超過 1 MiB。", 413)
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SteamPredictionError("invalid_csv_encoding", "CSV 必須使用 UTF-8 編碼。", 400) from exc
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader)
        if not header or any(not item.strip() for item in header):
            raise SteamPredictionError("invalid_csv_header", "CSV 標題列含空白欄位名稱。", 400)
        header = [item.strip() for item in header]
        if len(set(header)) != len(header):
            raise SteamPredictionError("duplicate_columns", "CSV 欄位名稱不得重複。", 400)
        required = set(MODEL_INPUT_FIELDS) | {"review_count"}
        if set(header) != required:
            raise SteamPredictionError("invalid_columns", "CSV 必須包含完整 Steam 輸入契約欄位，且不得有多餘欄位。", 400)
        records = list(reader)
    except StopIteration as exc:
        raise SteamPredictionError("empty_csv", "CSV 需要標題列與資料列。", 400) from exc
    except csv.Error as exc:
        raise SteamPredictionError("invalid_csv", "CSV 格式無法解析。", 400) from exc
    if not records:
        raise SteamPredictionError("empty_csv", "CSV 至少需要一筆資料。", 400)
    if len(records) > MAX_BATCH_ROWS:
        raise SteamPredictionError("too_many_rows", f"CSV 每次最多 {MAX_BATCH_ROWS} 筆資料。", 413)
    options = set(runtime.schema["genre_options"])
    columns = [*header, "row_number", "predicted_k", "review_count", "estimated_ownership", "fixed_k_30_ownership", "prediction_status", "error_code", "error_message"]
    output_rows: list[dict[str, Any]] = []
    for index, cells in enumerate(records, start=2):
        original = {name: cells[position] if position < len(cells) else "" for position, name in enumerate(header)}
        if len(cells) != len(header):
            output_rows.append({**original, "row_number": index, "prediction_status": "ERROR", "error_code": "invalid_row_width", "error_message": "資料欄數與標題不一致。"})
            continue
        try:
            inputs: dict[str, Any] = {}
            for field in MODEL_INPUT_FIELDS:
                raw = original[field].strip()
                if field == "genres":
                    inputs[field] = _genres_from_csv(raw, options)
                elif field in _BOOL_FIELDS:
                    normalized = raw.lower()
                    if normalized not in {"0", "1", "true", "false"}:
                        raise SteamPredictionError("invalid_boolean", "布林欄位只能使用 true 或 false。", field=field)
                    inputs[field] = normalized in {"1", "true"}
                else:
                    try:
                        inputs[field] = float(raw)
                    except ValueError as exc:
                        raise SteamPredictionError("invalid_number", "數值欄位必須是有限數字。", field=field) from exc
            try:
                review_count: Any = float(original["review_count"].strip())
            except ValueError as exc:
                raise SteamPredictionError("invalid_number", "review_count 必須是正整數。", field="review_count") from exc
            prediction = runtime.predict(inputs, review_count)
            output_rows.append({**original, "genres": "|".join(inputs["genres"]), "row_number": index,
                "predicted_k": prediction["predicted_k"], "review_count": prediction["review_count"],
                "estimated_ownership": prediction["estimated_ownership"],
                "fixed_k_30_ownership": prediction["fixed_k_30_ownership"],
                "prediction_status": "SUCCESS", "error_code": "", "error_message": ""})
        except SteamPredictionError as exc:
            output_rows.append({**original, "row_number": index, "prediction_status": "ERROR",
                "error_code": exc.code, "error_message": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError):
            output_rows.append({**original, "row_number": index, "prediction_status": "ERROR",
                "error_code": "invalid_row", "error_message": "資料列未通過輸入契約驗證。"})
    result = {
        **runtime.identity,
        "total_rows": len(output_rows),
        "success_rows": sum(row["prediction_status"] == "SUCCESS" for row in output_rows),
        "error_rows": sum(row["prediction_status"] == "ERROR" for row in output_rows),
        "columns": columns,
        "rows": output_rows,
    }
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_BATCH_RESPONSE_BYTES:
        raise SteamPredictionError("response_too_large", "批次結果超過安全回應上限。", 413)
    return result


def reset_runtime_for_tests() -> None:
    global _RUNTIME
    _RUNTIME = None
