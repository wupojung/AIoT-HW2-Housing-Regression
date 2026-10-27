"""Reusable Phase 6 inference functions for a serialized Ames model bundle."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from housing_regression.data_prep import ALL_PREDICTOR_COLUMNS, ID_COLUMN, TARGET_COLUMN


def load_model(model_path: str | Path) -> Any:
    """Load the model object from a trusted Phase 4 joblib bundle.

    Joblib artifacts use Python object serialization; only load files from a
    trusted source.
    """
    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib is unavailable; install the project Python requirements.") from exc

    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Model file does not exist: {path}")

    try:
        bundle = joblib.load(path)
    except Exception as exc:
        raise ValueError(f"Could not load Phase 4 joblib model bundle: {path}") from exc

    if not isinstance(bundle, dict) or "model" not in bundle:
        raise ValueError("The joblib file is not a supported Phase 4 model bundle (missing 'model').")

    model = bundle["model"]
    if not callable(getattr(model, "predict", None)):
        raise ValueError("The Phase 4 bundle's 'model' object does not provide predict().")
    return model


def _normalize_records(payload: Any) -> tuple[list[Mapping[str, Any]], bool]:
    """Validate one JSON-like record or a list of records."""
    is_single_record = isinstance(payload, dict)
    records = [payload] if is_single_record else payload

    if not isinstance(records, list) or not records:
        raise ValueError("Input must be one JSON object or a non-empty array of JSON objects.")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("Every input record must be a JSON object.")

    missing_by_record: list[str] = []
    expected = set(ALL_PREDICTOR_COLUMNS)
    for index, record in enumerate(records, start=1):
        if TARGET_COLUMN in record:
            raise ValueError(f"Record {index} contains target field {TARGET_COLUMN!r}; remove it before inference.")
        missing = sorted(expected - record.keys())
        if missing:
            missing_by_record.append(f"record {index}: {', '.join(missing)}")
    if missing_by_record:
        details = "; ".join(missing_by_record[:3])
        if len(missing_by_record) > 3:
            details += f"; and {len(missing_by_record) - 3} more record(s)"
        raise ValueError(f"Input is missing required Ames predictor columns: {details}")

    return records, is_single_record


def predict_records(model: Any, payload: Any) -> dict[str, Any] | list[dict[str, Any]]:
    """Predict a record or record list and return a JSON-compatible response.

    A single input object returns one result object. An input array returns an
    array of result objects. Each result contains the supplied Id, when present,
    and the predicted SalePrice.
    """
    records, is_single_record = _normalize_records(payload)
    values = model.predict(records)

    try:
        predictions = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError("The model returned predictions that are not numeric.") from exc
    if len(predictions) != len(records):
        raise ValueError("The model returned a different number of predictions than input records.")
    if not all(math.isfinite(value) for value in predictions):
        raise ValueError("The model returned a non-finite prediction.")

    results: list[dict[str, Any]] = []
    for record, prediction in zip(records, predictions):
        result: dict[str, Any] = {}
        if ID_COLUMN in record:
            result[ID_COLUMN] = record[ID_COLUMN]
        result[TARGET_COLUMN] = prediction
        results.append(result)

    return results[0] if is_single_record else results


def predict_json_text(model: Any, json_text: str) -> str:
    """Parse JSON text, predict, and serialize the direct JSON response."""
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON input: {exc.msg} at line {exc.lineno}, column {exc.colno}.") from exc
    result = predict_records(model, payload)
    return json.dumps(result, ensure_ascii=False, allow_nan=False)
