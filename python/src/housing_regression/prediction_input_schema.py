"""Export a Prediction Input Schema from a trusted fitted sklearn bundle.

The first adapter supports the CAR Final Fit bundle shape. The emitted schema
is data-driven: it never assumes a fixed number of raw or encoded features.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from housing_regression.contracts import ContractValidationError, validate_document


class PredictionInputSchemaError(ValueError):
    """Raised when fitted model metadata is incomplete or inconsistent."""


PREDICTION_INPUT_SCHEMA_CANONICAL = Path(
    "docs/contracts/schemas/prediction-input-schema-v0.1.schema.json"
)
PREDICTION_INPUT_SCHEMA_LEGACY = Path(
    "docs/design/data-contracts/schemas/prediction-input-schema-v0.1.schema.json"
)


def prediction_input_schema_path(repo_root: str | Path | None = None) -> Path:
    """Resolve the canonical contract path, with a bounded migration fallback.

    PR #66 relocates the Phase 1–6 schemas but currently leaves the separate
    Prediction Input Schema at its legacy path. Prefer the canonical location
    when that schema is migrated; use the legacy location only while it is
    absent. An existing but unsafe canonical entry fails closed.
    """
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    if root.is_symlink():
        raise PredictionInputSchemaError("Prediction Input repository root must not be a symlink")
    canonical = root / PREDICTION_INPUT_SCHEMA_CANONICAL
    legacy = root / PREDICTION_INPUT_SCHEMA_LEGACY
    for candidate in (canonical, legacy):
        current = root
        for part in candidate.relative_to(root).parts:
            current = current / part
            if current.is_symlink():
                raise PredictionInputSchemaError("Prediction Input JSON Schema path contains a symlink")
        if not candidate.exists() and not candidate.is_symlink():
            continue
        if candidate.is_symlink() or not candidate.is_file():
            raise PredictionInputSchemaError("Prediction Input JSON Schema path is not a regular file")
        return candidate
    raise PredictionInputSchemaError("Prediction Input JSON Schema is missing from canonical and migration paths")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _as_columns(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, slice):
        raise PredictionInputSchemaError("slice-based transformer columns are unsupported")
    try:
        columns = list(value)
    except TypeError as exc:
        raise PredictionInputSchemaError("could not determine transformer input columns") from exc
    if not all(isinstance(item, str) and item for item in columns):
        raise PredictionInputSchemaError("transformer input columns must be non-empty strings")
    return columns


def _pipeline_steps(transformer: Any) -> list[tuple[str, Any]]:
    if isinstance(transformer, Pipeline):
        return list(transformer.steps)
    return [("transformer", transformer)]


def _find_step(steps: list[tuple[str, Any]], expected_type: type) -> Any | None:
    matches = [step for _, step in steps if isinstance(step, expected_type)]
    if len(matches) > 1:
        raise PredictionInputSchemaError(f"multiple {expected_type.__name__} steps are unsupported")
    return matches[0] if matches else None


def _python_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PredictionInputSchemaError("encoder contains a non-finite category value")
        return value
    raise PredictionInputSchemaError("encoder category has an unsupported JSON value type")


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _source_for_encoded_name(encoded_name: str, raw_columns: list[str]) -> str:
    candidates = [name for name in raw_columns if encoded_name == name or encoded_name.startswith(name + "_")]
    if not candidates:
        raise PredictionInputSchemaError("could not trace an encoded feature to a raw input")
    if len(candidates) != 1:
        raise PredictionInputSchemaError("encoded feature lineage is ambiguous for overlapping raw input names")
    return candidates[0]


def _imputer_metadata(steps: list[tuple[str, Any]]) -> dict[str, Any]:
    imputer = _find_step(steps, SimpleImputer)
    if imputer is None:
        return {
            "nullable": None,
            "missing_policy": "UNKNOWN_NO_FITTED_IMPUTER",
            "missing_marker": None,
            "missing_evidence_status": "UNKNOWN",
        }
    if not hasattr(imputer, "statistics_"):
        raise PredictionInputSchemaError("imputer is not fitted")
    marker = imputer.missing_values
    marker_is_nan = isinstance(marker, (float, np.floating)) and math.isnan(float(marker))
    marker_name = "NaN" if marker_is_nan else str(marker)
    return {
        # `nullable` describes literal JSON null input, not merely whether
        # sklearn can impute its configured sentinel. NaN requires an API
        # normalization step that this metadata exporter cannot assert.
        "nullable": True if marker is None else None,
        "missing_policy": f"SIMPLE_IMPUTER_{str(imputer.strategy).upper()}",
        "missing_marker": marker_name,
        "missing_evidence_status": "VERIFIED",
    }


def _manifest_evidence(run_manifest: Mapping[str, Any] | None, bundle: Mapping[str, Any], model_sha256: str) -> dict[str, Any]:
    if run_manifest is None:
        return {
            "run_id": bundle.get("run_id"),
            "configuration_id": bundle.get("configuration_id"),
            "source_data_sha256": bundle.get("source_sha256"),
            "config_sha256": None,
            "code_sha256": None,
            "evidence_status": "PARTIAL",
            "manifest_verification": "NOT_PROVIDED",
        }

    integrity = run_manifest.get("integrity")
    if not isinstance(integrity, Mapping):
        raise PredictionInputSchemaError("run manifest has no integrity object")
    manifest_model_sha = integrity.get("final_model_sha256")
    if manifest_model_sha != model_sha256:
        raise PredictionInputSchemaError("run manifest model SHA does not match the model artifact")
    manifest_run_id = run_manifest.get("run_id")
    if manifest_run_id != bundle.get("run_id"):
        raise PredictionInputSchemaError("run manifest ID does not match the model bundle")
    manifest_source_sha = run_manifest.get("source_data_sha256")
    if manifest_source_sha != bundle.get("source_sha256"):
        raise PredictionInputSchemaError("run manifest source SHA does not match the model bundle")
    integrity_source_sha = integrity.get("source_sha256")
    if integrity_source_sha is not None and integrity_source_sha != manifest_source_sha:
        raise PredictionInputSchemaError("run manifest integrity source SHA is inconsistent")
    integrity_run_id = integrity.get("run_id")
    if integrity_run_id is not None and integrity_run_id != manifest_run_id:
        raise PredictionInputSchemaError("run manifest integrity Run ID is inconsistent")
    config_sha = integrity.get("config_sha256")
    code_sha = run_manifest.get("code_sha256")
    verified = _valid_sha256(config_sha) and _valid_sha256(code_sha)
    return {
        "run_id": manifest_run_id,
        "configuration_id": bundle.get("configuration_id"),
        "source_data_sha256": manifest_source_sha,
        "config_sha256": config_sha,
        "code_sha256": code_sha,
        "evidence_status": "VERIFIED" if verified else "PARTIAL",
        "manifest_verification": "MODEL_RUN_SOURCE_CONFIG_AND_CODE_BOUND" if verified else "PARTIAL_MANIFEST_METADATA",
    }


def build_prediction_input_schema(
    model_bundle: Mapping[str, Any],
    *,
    case_id: str,
    model_id: str,
    model_sha256: str,
    model_version: str | None = None,
    run_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build generic schema metadata from the supported fitted CAR bundle shape."""
    if not isinstance(model_bundle, Mapping):
        raise PredictionInputSchemaError("model bundle must be a mapping")
    if not case_id or not model_id:
        raise PredictionInputSchemaError("case_id and model_id are required")
    if not _valid_sha256(model_sha256):
        raise PredictionInputSchemaError("model_sha256 must be a 64-character SHA-256 digest")
    required_bundle_keys = {"transformer", "scaler", "mask", "estimator", "features", "run_id", "configuration_id", "source_sha256"}
    missing_bundle_keys = required_bundle_keys - set(model_bundle)
    if missing_bundle_keys:
        raise PredictionInputSchemaError("unsupported model bundle; required fitted metadata is missing")

    transformer = model_bundle["transformer"]
    if not all(hasattr(transformer, attribute) for attribute in ("feature_names_in_", "transformers_", "output_indices_", "get_feature_names_out")):
        raise PredictionInputSchemaError("unsupported preprocessing object; fitted ColumnTransformer metadata is required")
    training_columns = list(transformer.feature_names_in_)
    if not training_columns or not all(isinstance(name, str) and name for name in training_columns):
        raise PredictionInputSchemaError("fitted raw input feature names are unavailable")
    if len(set(training_columns)) != len(training_columns):
        raise PredictionInputSchemaError("fitted raw input feature names are not unique")
    if list(model_bundle["features"]) != training_columns:
        raise PredictionInputSchemaError("bundle raw feature order does not match fitted preprocessing")
    if not isinstance(model_bundle["run_id"], str) or not model_bundle["run_id"]:
        raise PredictionInputSchemaError("model Run ID is missing")
    if not isinstance(model_bundle["configuration_id"], str) or not model_bundle["configuration_id"]:
        raise PredictionInputSchemaError("model Configuration ID is missing")
    if not _valid_sha256(model_bundle["source_sha256"]):
        raise PredictionInputSchemaError("model source SHA-256 is missing or invalid")

    encoded_names = [str(name) for name in transformer.get_feature_names_out()]
    mask = np.asarray(model_bundle["mask"])
    if mask.ndim != 1 or len(mask) != len(encoded_names) or mask.dtype.kind != "b":
        raise PredictionInputSchemaError("selected-feature mask does not match encoded feature order")
    selected_indexes = np.flatnonzero(mask)
    estimator = model_bundle["estimator"]
    if getattr(estimator, "n_features_in_", None) != len(selected_indexes):
        raise PredictionInputSchemaError("selected feature count does not match fitted estimator input")
    scaler = model_bundle["scaler"]
    if getattr(scaler, "n_features_in_", None) != len(encoded_names):
        raise PredictionInputSchemaError("scaler input count does not match encoded feature count")

    raw_specs: dict[str, dict[str, Any]] = {}
    raw_to_encoded: dict[str, list[str]] = {}
    encoded_sources: dict[str, str] = {}
    observed_columns: list[str] = []
    for branch_name, branch, branch_columns_raw in transformer.transformers_:
        if branch_name == "remainder" and branch == "drop":
            continue
        branch_columns = _as_columns(branch_columns_raw)
        if branch == "drop":
            continue
        if branch == "passthrough":
            raise PredictionInputSchemaError("passthrough transformer metadata is unsupported in v0.1")
        steps = _pipeline_steps(branch)
        encoder = _find_step(steps, OneHotEncoder)
        imputer_info = _imputer_metadata(steps)
        supported_types = (SimpleImputer, OneHotEncoder)
        if any(not isinstance(step, supported_types) for _, step in steps):
            raise PredictionInputSchemaError("unsupported fitted transformer step; v0.1 supports imputer and OneHotEncoder metadata")
        branch_slice = transformer.output_indices_.get(branch_name)
        if not isinstance(branch_slice, slice) or branch_slice.start is None or branch_slice.stop is None:
            raise PredictionInputSchemaError("fitted transformer output positions are unavailable")
        branch_output_names = encoded_names[branch_slice]

        if encoder is not None:
            if not hasattr(encoder, "categories_") or len(encoder.categories_) != len(branch_columns):
                raise PredictionInputSchemaError("fitted encoder categories do not match its raw input columns")
            if encoder.handle_unknown not in {"error", "ignore", "infrequent_if_exist", "warn"}:
                raise PredictionInputSchemaError("unsupported OneHotEncoder unknown-category behavior")
            expected_branch_names = list(encoder.get_feature_names_out(input_features=branch_columns))
            if len(expected_branch_names) != len(branch_output_names):
                raise PredictionInputSchemaError("encoder output names do not match fitted transformer output")
            for column, categories, infrequent in zip(branch_columns, encoder.categories_, encoder.infrequent_categories_):
                raw_specs[column] = {
                    "data_type": "category",
                    "required": True,
                    "control_type": "select" if len(categories) <= 20 else "text",
                    "control_type_evidence": "PROPOSED_BY_FITTED_CATEGORY_CARDINALITY",
                    "options": [],
                    "unit": None,
                    "minimum": None,
                    "maximum": None,
                    "evidence_status": "VERIFIED",
                    "unknown_category_behavior": encoder.handle_unknown,
                    "api_allowlist_status": "NOT_ESTABLISHED",
                    "encoder_metadata": {
                        "name": "OneHotEncoder",
                        "minimum_frequency": _python_scalar(encoder.min_frequency),
                        "maximum_categories": _python_scalar(encoder.max_categories),
                        "infrequent_category_count": 0 if infrequent is None else len(infrequent),
                    },
                    "blank_policy": "TRAINED_CATEGORY_VALUE" if any(_python_scalar(item) == "" for item in categories) else "UNKNOWN_OR_UNKNOWN_CATEGORY",
                    **imputer_info,
                }
                infrequent_values = [] if infrequent is None else [_python_scalar(item) for item in infrequent]
                raw_specs[column]["options"] = [
                    {
                        "value": _python_scalar(item),
                        "source": "FITTED_ENCODER_CATEGORY",
                        "evidence_status": "VERIFIED",
                        "infrequent": _python_scalar(item) in infrequent_values,
                        "api_allowlisted": False,
                    }
                    for item in categories
                ]
                raw_to_encoded[column] = []
                observed_columns.append(column)
            for full_name, branch_name_out in zip(branch_output_names, expected_branch_names):
                source = _source_for_encoded_name(branch_name_out, branch_columns)
                raw_to_encoded[source].append(full_name)
                encoded_sources[full_name] = source
        else:
            if len(branch_output_names) != len(branch_columns):
                raise PredictionInputSchemaError("non-categorical transformer is not one-to-one; raw lineage is unknown")
            for column, full_name in zip(branch_columns, branch_output_names):
                raw_specs[column] = {
                    "data_type": "number",
                    "required": True,
                    "control_type": "number",
                    "control_type_evidence": "PROPOSED_FROM_NUMERIC_TRANSFORMER",
                    "options": [],
                    "unit": None,
                    "minimum": None,
                    "maximum": None,
                    "evidence_status": "VERIFIED",
                    "unknown_category_behavior": None,
                    "api_allowlist_status": "NOT_APPLICABLE",
                    "blank_policy": "REJECT_OR_NORMALIZE_BEFORE_TRANSFORM",
                    **imputer_info,
                }
                raw_to_encoded[column] = [full_name]
                encoded_sources[full_name] = column
                observed_columns.append(column)

    if len(observed_columns) != len(set(observed_columns)):
        raise PredictionInputSchemaError("raw input column appears in multiple fitted transformer branches")
    unexpected_columns = set(observed_columns) - set(training_columns)
    if unexpected_columns:
        raise PredictionInputSchemaError("transformer uses a raw column absent from fitted feature identity")
    runtime_columns = [name for name in training_columns if name in raw_specs]
    if not runtime_columns:
        raise PredictionInputSchemaError("no runtime input columns could be derived from fitted transformers")

    input_features = [
        {
            "name": name,
            **raw_specs[name],
            "encoded_features": raw_to_encoded[name],
        }
        for name in runtime_columns
    ]
    selected_encoded_features = [
        {"index": int(index), "name": encoded_names[index], "source_feature": encoded_sources.get(encoded_names[index])}
        for index in selected_indexes
    ]
    evidence = _manifest_evidence(run_manifest, model_bundle, model_sha256)
    for digest_name in ("source_data_sha256", "config_sha256", "code_sha256"):
        digest_value = evidence[digest_name]
        if digest_value is not None and not _valid_sha256(digest_value):
            raise PredictionInputSchemaError(f"source evidence {digest_name} is not a valid SHA-256 digest")
    document = {
        "schema_version": "0.1.0",
        "case_id": case_id,
        "model_id": model_id,
        "model_version": model_version,
        "model_sha256": model_sha256.lower(),
        "preprocessing_reference": {
            "bundle_type": "sklearn_column_transformer_scaler_mask_estimator",
            "raw_input_order": runtime_columns,
            "training_feature_count": len(training_columns),
            "unused_training_features": [name for name in training_columns if name not in raw_specs],
            "encoded_feature_count": len(encoded_names),
            "selected_encoded_feature_count": len(selected_encoded_features),
            "transform_order": ["transformer", "scaler", "selected_feature_mask", "estimator"],
        },
        "input_feature_count": len(input_features),
        "input_features": input_features,
        "selected_encoded_features": selected_encoded_features,
        "raw_to_encoded_mapping": [
            {"raw_name": name, "encoded_names": raw_to_encoded[name]}
            for name in runtime_columns
        ],
        "source_evidence": evidence,
        "api_readiness": "BLOCKED_NOT_AN_API_ALLOWLIST_OR_ENDPOINT",
        "category_values_publication_review": "REQUIRED_BEFORE_PUBLICATION",
        "status": "VERIFIED" if evidence["evidence_status"] == "VERIFIED" else "PARTIAL",
    }
    schema_path = prediction_input_schema_path()
    try:
        validate_document(document, schema_path)
    except ContractValidationError as exc:
        raise PredictionInputSchemaError(f"generated Prediction Input Schema is invalid: {exc}") from exc
    return document


def write_schema_new(path: str | Path, document: Mapping[str, Any]) -> Path:
    """Write JSON to a new path only; fail closed when output already exists."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise PredictionInputSchemaError("refusing to overwrite an existing schema file") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
    except Exception:
        try:
            destination.unlink()
        except OSError:
            pass
        raise
    return destination
