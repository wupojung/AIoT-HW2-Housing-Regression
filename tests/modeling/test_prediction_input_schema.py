"""Synthetic tests for generic Prediction Input Schema export."""

from __future__ import annotations

import json
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from housing_regression.prediction_input_schema import (
    PredictionInputSchemaError,
    _imputer_metadata,
    _source_for_encoded_name,
    build_prediction_input_schema,
    prediction_input_schema_path,
    write_schema_new,
)
from housing_regression.contracts import validate_document
from tools.modeling.export_prediction_input_schema import _load_verified_bundle


class PredictionInputSchemaTests(unittest.TestCase):
    def _bundle(self, raw_count: int) -> dict:
        numeric_count = max(1, raw_count // 3)
        categorical_count = raw_count - numeric_count
        numeric_fields = [f"number_{index}" for index in range(numeric_count)]
        categorical_fields = [f"category_{index}" for index in range(categorical_count)]
        columns = numeric_fields + categorical_fields
        row_count = 30
        values = {}
        for index, name in enumerate(numeric_fields):
            values[name] = np.arange(row_count, dtype=float) + index
            values[name][0] = np.nan
        for index, name in enumerate(categorical_fields):
            values[name] = np.array(["alpha", "beta"] * (row_count // 2), dtype=object)
            values[name][0] = None
        frame = pd.DataFrame(values, columns=columns)

        numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
        categorical_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=2)),
        ])
        transformer = ColumnTransformer(
            [("num", numeric_pipe, numeric_fields), ("cat", categorical_pipe, categorical_fields)],
            remainder="drop",
            sparse_threshold=0.0,
        ).fit(frame)
        transformed = transformer.transform(frame)
        scaler = StandardScaler().fit(transformed)
        mask = np.ones(transformed.shape[1], dtype=bool)
        if transformed.shape[1] > 1:
            mask[-1] = False
        estimator = LinearRegression().fit(scaler.transform(transformed)[:, mask], np.arange(row_count, dtype=float))
        return {
            "transformer": transformer,
            "scaler": scaler,
            "mask": mask,
            "estimator": estimator,
            "features": columns,
            "target": "synthetic_target",
            "configuration_id": f"synthetic-config-{raw_count}",
            "run_id": f"synthetic-run-{raw_count}",
            "source_sha256": "a" * 64,
            # These fields must never be serialized into the input schema.
            "private_training_record": "SYNTHETIC_PRIVATE_ROW_SENTINEL",
            "oof_values": [999, 1000],
            "holdout_values": [1001],
            "estimator_coefficients": [123.45],
        }

    def _manifest(self, bundle: dict, model_sha: str = "b" * 64) -> dict:
        return {
            "run_id": bundle["run_id"],
            "source_data_sha256": bundle["source_sha256"],
            "code_sha256": "c" * 64,
            "integrity": {
                "final_model_sha256": model_sha,
                "source_sha256": bundle["source_sha256"],
                "config_sha256": "d" * 64,
            },
        }

    def test_exports_five_raw_inputs_without_fixed_count(self):
        bundle = self._bundle(5)
        document = build_prediction_input_schema(
            bundle, case_id="synthetic-five", model_id="model-five", model_sha256="b" * 64
        )
        self.assertEqual(document["input_feature_count"], 5)
        self.assertEqual(len(document["input_features"]), 5)
        self.assertEqual(document["status"], "PARTIAL")

    def test_exports_fifteen_raw_inputs_and_verified_manifest_binding(self):
        bundle = self._bundle(15)
        document = build_prediction_input_schema(
            bundle,
            case_id="synthetic-fifteen",
            model_id="model-fifteen",
            model_sha256="b" * 64,
            run_manifest=self._manifest(bundle),
        )
        self.assertEqual(document["input_feature_count"], 15)
        self.assertEqual(len(document["input_features"]), 15)
        self.assertEqual(document["source_evidence"]["evidence_status"], "VERIFIED")
        self.assertEqual(document["status"], "VERIFIED")

    def test_category_options_preserve_fitted_source_values(self):
        document = build_prediction_input_schema(
            self._bundle(5), case_id="synthetic-five", model_id="model-five", model_sha256="b" * 64
        )
        categorical = next(item for item in document["input_features"] if item["data_type"] == "category")
        self.assertEqual([option["value"] for option in categorical["options"]], ["alpha", "beta"])
        self.assertTrue(all(option["api_allowlisted"] is False for option in categorical["options"]))
        self.assertEqual(categorical["unknown_category_behavior"], "ignore")

    def test_numeric_fields_use_number_control_without_invented_limits(self):
        document = build_prediction_input_schema(
            self._bundle(5), case_id="synthetic-five", model_id="model-five", model_sha256="b" * 64
        )
        numeric = next(item for item in document["input_features"] if item["data_type"] == "number")
        self.assertEqual(numeric["control_type"], "number")
        self.assertIsNone(numeric["unit"])
        self.assertIsNone(numeric["minimum"])
        self.assertIsNone(numeric["maximum"])
        categorical = next(item for item in document["input_features"] if item["data_type"] == "category")
        self.assertIsNone(categorical["nullable"], "NaN sentinel does not prove literal JSON null support")

    def test_nullable_true_requires_literal_none_imputer_sentinel(self):
        imputer = SimpleImputer(strategy="most_frequent", missing_values=None).fit(
            np.array([[None], ["known"]], dtype=object)
        )
        metadata = _imputer_metadata([("imputer", imputer)])
        self.assertIs(metadata["nullable"], True)
        self.assertEqual(metadata["missing_marker"], "None")

    def test_unknown_preprocessing_metadata_fails_closed(self):
        bundle = self._bundle(5)
        bundle["transformer"] = object()
        with self.assertRaisesRegex(PredictionInputSchemaError, "fitted ColumnTransformer metadata"):
            build_prediction_input_schema(bundle, case_id="case", model_id="model", model_sha256="b" * 64)

    def test_declared_input_count_matches_feature_array_and_schema_validates(self):
        document = build_prediction_input_schema(
            self._bundle(15), case_id="synthetic-fifteen", model_id="model-fifteen", model_sha256="b" * 64
        )
        self.assertEqual(document["input_feature_count"], len(document["input_features"]))
        validate_document(document, prediction_input_schema_path())

    def test_documented_mock_example_validates(self):
        root = Path(__file__).resolve().parents[2]
        example = json.loads((root / "docs/design/data-contracts/examples/prediction-input-schema.example.json").read_text(encoding="utf-8"))
        schema_path = prediction_input_schema_path(root)
        validate_document(example, schema_path)
        self.assertEqual(example["input_feature_count"], len(example["input_features"]))

    def test_schema_path_prefers_canonical_then_uses_legacy_until_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            canonical = root / "docs/contracts/schemas/prediction-input-schema-v0.1.schema.json"
            legacy = root / "docs/design/data-contracts/schemas/prediction-input-schema-v0.1.schema.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("{}", encoding="utf-8")

            # A Phase schema registry directory alone does not migrate the
            # separate Prediction Input Schema; the existing legacy file is used.
            (root / "docs/contracts/schemas").mkdir(parents=True)
            (root / "docs/contracts/schemas/phase-01.schema.json").write_text("{}", encoding="utf-8")
            self.assertEqual(prediction_input_schema_path(root), legacy)

            canonical.write_text("{\"canonical\":true}", encoding="utf-8")
            self.assertEqual(prediction_input_schema_path(root), canonical)

    def test_schema_path_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(PredictionInputSchemaError, "missing"):
                prediction_input_schema_path(temp)

    def test_manifest_identity_mismatch_fails_closed(self):
        bundle = self._bundle(5)
        manifest = self._manifest(bundle)
        manifest["integrity"]["run_id"] = "different-run"
        with self.assertRaisesRegex(PredictionInputSchemaError, "integrity Run ID is inconsistent"):
            build_prediction_input_schema(
                bundle,
                case_id="synthetic-five",
                model_id="model-five",
                model_sha256="b" * 64,
                run_manifest=manifest,
            )

    def test_ambiguous_raw_name_prefix_fails_closed(self):
        with self.assertRaisesRegex(PredictionInputSchemaError, "lineage is ambiguous"):
            _source_for_encoded_name("vehicle_make_model", ["vehicle", "vehicle_make"])

    def test_export_excludes_model_contents_and_research_rows(self):
        bundle = self._bundle(5)
        document = build_prediction_input_schema(
            bundle, case_id="synthetic-five", model_id="model-five", model_sha256="b" * 64
        )
        payload = json.dumps(document)
        for private_marker in ("SYNTHETIC_PRIVATE_ROW_SENTINEL", "estimator_coefficients", "oof_values", "holdout_values", "123.45"):
            self.assertNotIn(private_marker, payload)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "prediction-input-schema.json"
            output.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(PredictionInputSchemaError, "refusing to overwrite"):
                write_schema_new(output, {})
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")

    def test_artifact_hash_is_checked_before_deserialization(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "untrusted.joblib"
            artifact.write_bytes(b"not a joblib artifact")
            with self.assertRaisesRegex(PredictionInputSchemaError, "does not match"):
                _load_verified_bundle(artifact, "0" * 64)

    def test_path_replacement_after_hash_does_not_change_loaded_bytes(self):
        import joblib

        expected_bundle = {"trusted": "verified-bytes"}
        serialized = io.BytesIO()
        joblib.dump(expected_bundle, serialized)
        payload = serialized.getvalue()
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "trusted.joblib"
            artifact.write_bytes(payload)
            real_load = joblib.load

            def replace_path_then_load(verified_stream):
                artifact.write_bytes(b"replacement-after-hash")
                verified_stream.seek(0)
                return real_load(verified_stream)

            with patch("joblib.load", side_effect=replace_path_then_load):
                loaded, actual = _load_verified_bundle(artifact, digest)
            self.assertEqual(loaded, expected_bundle)
            self.assertEqual(actual, digest)
            self.assertEqual(artifact.read_bytes(), b"replacement-after-hash")


if __name__ == "__main__":
    unittest.main()
