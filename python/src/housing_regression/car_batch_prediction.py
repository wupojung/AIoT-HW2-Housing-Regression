"""Bounded in-memory CSV validation and prediction for the local CAR API."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Mapping

from housing_regression.local_car_prediction_api import (
    PredictionApiError,
    validate_inputs,
)

MAX_BATCH_REQUEST_BYTES = 1024 * 1024
MAX_BATCH_ROWS = 100
# Leave headroom below Vercel's 4.5 MB function response limit.
MAX_BATCH_RESPONSE_BYTES = 4_000_000
_RESULT_COLUMNS = (
    "row_number",
    "prediction",
    "prediction_unit",
    "prediction_status",
    "warning_code",
    "error_code",
    "error_message",
)


def batch_result_columns(contract: Mapping[str, Any]) -> list[str]:
    fields = contract.get("input_features")
    if not isinstance(fields, list):
        raise PredictionApiError("schema_unavailable", "模型輸入契約不可用。", 503)
    names = [field.get("name") for field in fields if isinstance(field, dict)]
    if len(names) != len(fields) or not all(isinstance(name, str) and name for name in names):
        raise PredictionApiError("schema_unavailable", "模型輸入契約欄位不可用。", 503)
    if len(names) != len(set(names)) or set(names).intersection(_RESULT_COLUMNS):
        raise PredictionApiError("schema_unavailable", "模型輸入契約與批次結果欄位衝突。", 503)
    return names + list(_RESULT_COLUMNS)


def _parse_csv(payload: bytes, expected_names: list[str]) -> tuple[list[str], list[tuple[int, list[str]]]]:
    if not isinstance(payload, bytes) or not payload:
        raise PredictionApiError("empty_csv", "CSV 檔案沒有內容。", 400)
    if len(payload) > MAX_BATCH_REQUEST_BYTES:
        raise PredictionApiError("request_too_large", "CSV 檔案超過 1 MiB 上限。", 413)
    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise PredictionApiError("invalid_csv_encoding", "CSV 必須使用 UTF-8 編碼。", 400) from exc

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = next(reader)
        if not headers or not any(header for header in headers):
            raise PredictionApiError("invalid_csv_header", "CSV 標題列不可空白。", 400)
        if len(headers) != len(set(headers)):
            raise PredictionApiError("duplicate_csv_headers", "CSV 標題列包含重複欄位。", 422)
        missing = [name for name in expected_names if name not in headers]
        extra = [name for name in headers if name not in expected_names]
        if missing or extra:
            raise PredictionApiError(
                "csv_header_mismatch",
                "CSV 欄位必須與目前模型輸入契約完全一致。",
                422,
                missing + extra,
            )
        records: list[tuple[int, list[str]]] = []
        previous_physical_line = reader.line_num
        for row in reader:
            if len(records) >= MAX_BATCH_ROWS:
                raise PredictionApiError("too_many_rows", "CSV 最多可包含 100 筆資料列。", 413)
            source_line = previous_physical_line + 1
            previous_physical_line = reader.line_num
            records.append((source_line, row))
    except StopIteration as exc:
        raise PredictionApiError("empty_csv", "CSV 必須包含標題列與資料列。", 400) from exc
    except csv.Error as exc:
        raise PredictionApiError("invalid_csv", "CSV 格式錯誤，請檢查引號與分隔符號。", 400) from exc
    if not records:
        raise PredictionApiError("empty_csv", "CSV 必須包含至少一筆資料列。", 400)
    return headers, records


def _typed_inputs(
    row: list[str], headers: list[str], contract: Mapping[str, Any]
) -> tuple[dict[str, str], dict[str, Any]]:
    raw = {name: row[index] for index, name in enumerate(headers) if index < len(row)}
    by_name = {field["name"]: field for field in contract["input_features"]}
    typed: dict[str, Any] = {}
    for name in (field["name"] for field in contract["input_features"]):
        if name not in raw:
            continue
        value = raw[name]
        field = by_name[name]
        if value == "" and field.get("nullable") is True:
            if field.get("data_type") != "category" or not any(
                isinstance(option, dict) and option.get("value") == ""
                for option in field.get("options", [])
            ):
                typed[name] = None
                continue
        if field.get("data_type") == "number" and value.strip():
            try:
                typed[name] = float(value)
            except ValueError:
                typed[name] = value
        else:
            typed[name] = value
    return raw, typed


def predict_csv_batch(runtime: Any, payload: bytes) -> dict[str, Any]:
    """Validate a complete CSV, then predict each valid row independently.

    CSV structure and limits are checked before the first model call. Uploaded
    bytes and row values remain in memory and are never logged or persisted.
    """
    contract = runtime.contract
    columns = batch_result_columns(contract)
    input_names = columns[:-len(_RESULT_COLUMNS)]
    headers, records = _parse_csv(payload, input_names)
    rows: list[dict[str, Any]] = []
    successful = 0
    for source_line, csv_row in records:
        raw_inputs, typed_inputs = _typed_inputs(csv_row, headers, contract)
        item: dict[str, Any] = {
            "row_number": source_line,
            "input": raw_inputs,
            "prediction": None,
            "prediction_unit": None,
            "status": "ERROR",
            "warning_code": None,
            "error_code": None,
            "error_message": None,
            "error_fields": [],
        }
        if len(csv_row) != len(headers):
            item["error_code"] = "csv_row_width_mismatch"
            item["error_message"] = "資料列欄位數與標題列不一致。"
            rows.append(item)
            continue
        try:
            normalized = validate_inputs(contract, typed_inputs)
            result = runtime.predict(normalized)
            item["prediction"] = result["prediction"]
            item["prediction_unit"] = result.get("unit")
            item["status"] = "SUCCESS"
            if result["prediction"] < 0:
                item["warning_code"] = "negative_prediction"
            successful += 1
        except PredictionApiError as exc:
            item["error_code"] = exc.code
            item["error_message"] = str(exc)
            item["error_fields"] = exc.fields
        except Exception:
            # Do not serialize an unexpected exception or request values.
            item["error_code"] = "inference_failed"
            item["error_message"] = "模型無法處理此資料列；未顯示預測結果。"
        rows.append(item)

    document = {
        "case_id": contract["case_id"],
        "model_id": contract["model_id"],
        "model_version": contract["model_version"],
        "run_id": contract["source_evidence"]["run_id"],
        "configuration_id": contract["source_evidence"]["configuration_id"],
        "schema_sha256": runtime.schema_sha256,
        "columns": columns,
        "total_rows": len(rows),
        "valid_rows": successful,
        "error_rows": len(rows) - successful,
        "rows": rows,
    }
    encoded = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_BATCH_RESPONSE_BYTES:
        raise PredictionApiError("batch_response_too_large", "批次結果超過安全回應上限。", 413)
    return document
