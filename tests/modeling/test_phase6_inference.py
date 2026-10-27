"""Synthetic contract tests for the Phase 6 inference functions and CLI."""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
CLI_DIR = REPO_ROOT / "tools" / "modeling"
for entry in (str(SRC_DIR), str(CLI_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import run_phase6_inference as cli  # noqa: E402
from housing_regression.data_prep import ALL_PREDICTOR_COLUMNS, ID_COLUMN, TARGET_COLUMN  # noqa: E402
from housing_regression.phase6_inference import (  # noqa: E402
    load_model,
    load_model_bundle,
    predict_json_text,
    predict_records,
)
from housing_regression.modeling.p4b_final_model import FinalP4BDevelopmentModel  # noqa: E402


class FixedModel:
    """Tiny deterministic model used only with synthetic records."""

    def __init__(self, values: list[float] | None = None):
        self.values = values
        self.received: list[dict[str, str]] | None = None

    def predict(self, records):
        self.received = records
        if self.values is not None:
            return self.values
        return [100_000.0 + 1_000.0 * index for index, _ in enumerate(records)]


class SyntheticFittedPipeline:
    is_fitted = True

    def transform(self, records, split_name):
        return SimpleNamespace(
            feature_names=["LotArea"],
            to_numpy=lambda: np.asarray(
                [[float(record.get("LotArea") or 0.0)] for record in records],
                dtype=np.float64,
            ),
        )


def make_record(record_id: str, target: str | None = None) -> dict[str, str]:
    row = {column: "" for column in ALL_PREDICTOR_COLUMNS}
    row[ID_COLUMN] = record_id
    row["LotArea"] = ""
    row["Neighborhood"] = ""
    if target is not None:
        row[TARGET_COLUMN] = target
    return row


def write_csv(path: Path, rows: list[dict[str, str]], include_target: bool) -> list[str]:
    headers = [ID_COLUMN, *ALL_PREDICTOR_COLUMNS]
    if include_target:
        headers.append(TARGET_COLUMN)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return headers


class Phase6InferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="phase6-synthetic-test-"))
        self.model_path = self.temp_dir / "synthetic-model.joblib"
        self.metadata = {
            "run_id": "synthetic-run-01",
            "artifact_type": "synthetic-test-model",
            "code_head_commit": "synthetic-code-sha",
        }
        joblib.dump({"model": FixedModel(), "metadata": self.metadata}, self.model_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_joblib_bundle_loader_returns_model_and_provenance(self):
        model, metadata = load_model_bundle(self.model_path)
        self.assertIsInstance(model, FixedModel)
        self.assertEqual(metadata, self.metadata)
        self.assertIsInstance(load_model(self.model_path), FixedModel)

    def test_json_object_and_array_accept_blank_feature_values(self):
        model = FixedModel()
        one = make_record("A-1")
        result = predict_records(model, one)
        self.assertEqual(result, {ID_COLUMN: "A-1", TARGET_COLUMN: 100_000.0})
        self.assertIsInstance(model.received, list)
        self.assertEqual(model.received[0]["LotArea"], "")
        self.assertEqual(model.received[0]["Neighborhood"], "")

        response = json.loads(predict_json_text(model, json.dumps([one, make_record("A-2")])))
        self.assertEqual(response, [
            {ID_COLUMN: "A-1", TARGET_COLUMN: 100_000.0},
            {ID_COLUMN: "A-2", TARGET_COLUMN: 101_000.0},
        ])

    def test_phase4_model_wrapper_accepts_json_records_with_missing_numeric_and_category_values(self):
        model = FinalP4BDevelopmentModel(
            preprocessing_pipeline=SyntheticFittedPipeline(),
            selected_feature_names=("LotArea",),
            ols_coefficients=np.asarray([10.0, 2.0]),
            metadata={"run_id": "synthetic-final-fit"},
        )
        record = make_record("A-1")
        result = predict_records(model, record)
        self.assertEqual(result, {ID_COLUMN: "A-1", TARGET_COLUMN: 10.0})

    def test_json_rejects_malformed_missing_wrong_type_and_target_inputs(self):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            predict_json_text(FixedModel(), "{")
        with self.assertRaisesRegex(ValueError, "missing required Ames predictor columns"):
            predict_records(FixedModel(), {ID_COLUMN: "A-1"})
        with self.assertRaisesRegex(ValueError, "Every input record"):
            predict_records(FixedModel(), [1, 2])
        target_record = make_record("A-1", "123456")
        with self.assertRaisesRegex(ValueError, "remove it before inference"):
            predict_records(FixedModel(), target_record)

    def test_cli_json_mode_reports_malformed_json_without_creating_output(self):
        output_path = self.temp_dir / "malformed-response.json"
        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--json", "{", "--output", str(output_path)
        ])
        self.assertEqual(code, 2)
        self.assertIn("Invalid JSON", stderr)
        self.assertFalse(output_path.exists())

    def test_prediction_rejects_nonfinite_and_wrong_length_model_outputs(self):
        with self.assertRaisesRegex(ValueError, "non-finite prediction"):
            predict_records(FixedModel([float("inf")]), make_record("A-1"))
        with self.assertRaisesRegex(ValueError, "different number of predictions"):
            predict_records(FixedModel([]), make_record("A-1"))

    def test_no_argument_mode_writes_header_only_template_and_obeys_force(self):
        original_cwd = Path.cwd()
        try:
            os.chdir(self.temp_dir)
            code, stdout, _stderr = self.run_cli([])
            self.assertEqual(code, 0, stdout)
            template = self.temp_dir / "inference-input-template.csv"
            with template.open("r", encoding="utf-8", newline="") as stream:
                reader = csv.reader(stream)
                header = next(reader)
                self.assertEqual(list(reader), [])
            self.assertEqual(header, [ID_COLUMN, *ALL_PREDICTOR_COLUMNS])

            code, _stdout, stderr = self.run_cli([])
            self.assertEqual(code, 2)
            self.assertIn("already exists", stderr)
            code, _stdout, _stderr = self.run_cli(["--force"])
            self.assertEqual(code, 0)
        finally:
            os.chdir(original_cwd)

        output_directory = self.temp_dir / "directory-is-not-a-file"
        output_directory.mkdir()
        code, _stdout, stderr = self.run_cli(["--output", str(output_directory), "--force"])
        self.assertEqual(code, 2)
        self.assertIn("is a directory", stderr)

    def test_labeled_csv_overwrites_target_and_writes_aggregate_report(self):
        input_path = self.temp_dir / "houses.csv"
        output_path = self.temp_dir / "predictions.csv"
        rows = [
            make_record("A-1", "120000"),
            make_record("A-2", ""),
            make_record("A-3", "0"),
        ]
        headers = write_csv(input_path, rows, include_target=True)
        source_bytes = input_path.read_bytes()
        code, stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path)
        ])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(input_path.read_bytes(), source_bytes)

        with output_path.open("r", encoding="utf-8", newline="") as stream:
            output_rows = list(csv.DictReader(stream))
        self.assertEqual([row[TARGET_COLUMN] for row in output_rows], ["100000.0", "101000.0", "102000.0"])
        self.assertEqual(list(output_rows[0]), headers)
        for source, output in zip(rows, output_rows):
            for column in headers:
                if column != TARGET_COLUMN:
                    self.assertEqual(output[column], source[column])
        self.assertIn("Replaced existing SalePrice values for 2 row(s)", stdout)

        report_path = self.temp_dir / "predictions-evaluation.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "LOCAL_DIAGNOSTIC_NOT_PHASE5")
        self.assertFalse(report["evaluation_scope"]["phase5_evaluation"])
        self.assertFalse(report["evaluation_scope"]["case_package_release_approved"])
        self.assertEqual(report["counts"], {
            "rows_predicted": 3,
            "rows_evaluated": 2,
            "rows_without_actual": 1,
        })
        self.assertEqual(report["model"]["run_id"], "synthetic-run-01")
        self.assertEqual(report["model"]["artifact_sha256"], hashlib.sha256(self.model_path.read_bytes()).hexdigest())
        self.assertEqual(report["source"]["file_sha256"], hashlib.sha256(source_bytes).hexdigest())
        self.assertEqual(report["prediction_file_sha256"], hashlib.sha256(output_path.read_bytes()).hexdigest())
        self.assertNotIn("A-1", report_text := report_path.read_text(encoding="utf-8"))
        self.assertNotIn("actual_values", report_text)

    def test_unlabeled_csv_adds_predictions_without_evaluation_json(self):
        input_path = self.temp_dir / "unlabeled.csv"
        output_path = self.temp_dir / "unlabeled-predictions.csv"
        rows = [make_record("A-1"), make_record("A-2")]
        headers = write_csv(input_path, rows, include_target=False)
        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path)
        ])
        self.assertEqual(code, 0, stderr)
        self.assertTrue(output_path.exists())
        self.assertFalse(output_path.with_name("unlabeled-predictions-evaluation.json").exists())
        with output_path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, [*headers, TARGET_COLUMN])
            self.assertEqual([row[TARGET_COLUMN] for row in reader], ["100000.0", "101000.0"])

    def test_cli_json_mode_returns_direct_json_result(self):
        record = make_record("A-1")
        code, stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--json", json.dumps(record)
        ])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), {ID_COLUMN: "A-1", TARGET_COLUMN: 100_000.0})

    def test_invalid_actual_value_fails_before_writing_either_output(self):
        input_path = self.temp_dir / "invalid-labels.csv"
        output_path = self.temp_dir / "invalid-predictions.csv"
        write_csv(input_path, [make_record("A-1", "not-a-number")], include_target=True)
        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path)
        ])
        self.assertEqual(code, 2)
        self.assertIn("non-numeric SalePrice", stderr)
        self.assertFalse(output_path.exists())
        self.assertFalse(output_path.with_name("invalid-predictions-evaluation.json").exists())

    def test_csv_missing_required_predictor_column_fails_before_output(self):
        input_path = self.temp_dir / "missing-column.csv"
        output_path = self.temp_dir / "missing-column-predictions.csv"
        headers = [ID_COLUMN, *[column for column in ALL_PREDICTOR_COLUMNS if column != "LotArea"]]
        with input_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=headers)
            writer.writeheader()
            writer.writerow({ID_COLUMN: "A-1"})

        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path)
        ])
        self.assertEqual(code, 2)
        self.assertIn("missing required Ames predictor columns", stderr)
        self.assertFalse(output_path.exists())

    def test_r2_is_null_for_single_or_constant_actual_values(self):
        predictions = [{TARGET_COLUMN: 90.0}, {TARGET_COLUMN: 110.0}]
        single = cli._build_evaluation_report(
            [{TARGET_COLUMN: "100"}], predictions[:1], "pred.csv", "a", "b", "c", {}
        )
        constant = cli._build_evaluation_report(
            [{TARGET_COLUMN: "100"}, {TARGET_COLUMN: "100"}], predictions, "pred.csv", "a", "b", "c", {}
        )
        self.assertIsNone(single["metrics"]["r2"])
        self.assertEqual(single["metrics"]["r2_status"], "UNDEFINED_INSUFFICIENT_ROWS")
        self.assertIsNone(constant["metrics"]["r2"])
        self.assertEqual(constant["metrics"]["r2_status"], "UNDEFINED_CONSTANT_ACTUALS")

    def test_output_collisions_require_force(self):
        input_path = self.temp_dir / "collision-input.csv"
        output_path = self.temp_dir / "collision-output.csv"
        rows = [make_record("A-1", "100000")]
        write_csv(input_path, rows, include_target=True)
        output_path.write_text("old prediction\n", encoding="utf-8")
        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path)
        ])
        self.assertEqual(code, 2)
        self.assertIn("already exists", stderr)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "old prediction\n")

        code, stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path), "--force"
        ])
        self.assertEqual(code, 0, stderr)
        self.assertIn("Evaluation summary written", stdout)
        self.assertTrue(output_path.with_name("collision-output-evaluation.json").exists())

    def test_no_label_rerun_with_force_removes_stale_evaluation_report(self):
        input_path = self.temp_dir / "stale-input.csv"
        output_path = self.temp_dir / "stale-output.csv"
        report_path = self.temp_dir / "stale-output-evaluation.json"

        write_csv(input_path, [make_record("A-1", "100000")], include_target=True)
        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path)
        ])
        self.assertEqual(code, 0, stderr)
        self.assertTrue(report_path.exists())

        write_csv(input_path, [make_record("A-1")], include_target=False)
        code, stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path), "--force"
        ])
        self.assertEqual(code, 0, stderr)
        self.assertFalse(report_path.exists())
        self.assertIn("Removed the stale evaluation summary", stdout)

    def test_sidecar_collision_is_checked_before_prediction_output_write(self):
        input_path = self.temp_dir / "sidecar-collision-input.csv"
        output_path = self.temp_dir / "sidecar-collision.csv"
        report_path = self.temp_dir / "sidecar-collision-evaluation.json"
        write_csv(input_path, [make_record("A-1", "100000")], include_target=True)
        report_path.write_text("old report", encoding="utf-8")

        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path)
        ])
        self.assertEqual(code, 2)
        self.assertIn("already exists", stderr)
        self.assertFalse(output_path.exists())
        self.assertEqual(report_path.read_text(encoding="utf-8"), "old report")

    def test_second_artifact_failure_rolls_back_both_previous_outputs(self):
        input_path = self.temp_dir / "rollback-input.csv"
        output_path = self.temp_dir / "rollback.csv"
        report_path = self.temp_dir / "rollback-evaluation.json"
        old_output = b"old predictions\n"
        old_report = b"old evaluation\n"
        output_path.write_bytes(old_output)
        report_path.write_bytes(old_report)
        write_csv(input_path, [make_record("A-1", "100000")], include_target=True)

        real_replace = os.replace
        failed_once = False

        def fail_evaluation_promotion_once(source, destination):
            nonlocal failed_once
            if Path(destination).resolve() == report_path.resolve() and ".tmp-" in Path(source).name and not failed_once:
                failed_once = True
                raise OSError("synthetic sidecar promotion failure")
            return real_replace(source, destination)

        with patch.object(cli.os, "replace", side_effect=fail_evaluation_promotion_once):
            code, _stdout, stderr = self.run_cli([
                "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(output_path), "--force"
            ])
        self.assertEqual(code, 2)
        self.assertIn("previous output files were restored", stderr)
        self.assertEqual(output_path.read_bytes(), old_output)
        self.assertEqual(report_path.read_bytes(), old_report)
        self.assertEqual(list(self.temp_dir.glob(".*.tmp-*")), [])
        self.assertEqual(list(self.temp_dir.glob(".*.bak-*")), [])

    def test_csv_input_and_model_artifacts_cannot_be_output_targets(self):
        input_path = self.temp_dir / "protected-input.csv"
        write_csv(input_path, [make_record("A-1")], include_target=False)
        source_bytes = input_path.read_bytes()
        code, _stdout, stderr = self.run_cli([
            "--model", str(self.model_path), "--input-csv", str(input_path), "--output", str(input_path)
        ])
        self.assertEqual(code, 2)
        self.assertIn("must not overwrite", stderr)
        self.assertEqual(input_path.read_bytes(), source_bytes)


if __name__ == "__main__":
    unittest.main()
