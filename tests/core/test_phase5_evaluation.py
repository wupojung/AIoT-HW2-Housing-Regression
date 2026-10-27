from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python" / "src"))

from housing_regression.phase5_evaluation import build_development_oof_evaluation
from housing_regression.contracts import validate_document


class Phase5EvaluationTests(unittest.TestCase):
    def test_synthetic_oof_handoff_recalculates_metrics_and_validates_contract(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        schema = repo / "docs/ui-ux/case-package/phase-05/evaluation-index.schema.json"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            oof = root / "oof.csv"
            meta_path = root / "oof.csv.metadata.json"
            output = root / "package"
            output.mkdir()
            n = 1168
            actual = np.linspace(75000, 425000, n)
            predicted = actual + np.sin(np.arange(n)) * 4000
            folds = np.asarray([0] * 390 + [1] * 389 + [2] * 389)
            fold_metrics = []
            for fold in range(3):
                mask = folds == fold
                residual = actual[mask] - predicted[mask]
                fold_metrics.append({
                    "fold": fold, "mae": float(np.mean(np.abs(residual))),
                    "rmse": float(np.sqrt(np.mean(residual ** 2))),
                    "r2": float(1 - np.sum(residual ** 2) / np.sum((actual[mask] - np.mean(actual[mask])) ** 2)),
                })
            with oof.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["run_id", "configuration_id", "fold", "row_id", "actual", "predicted"], lineterminator="\n")
                writer.writeheader()
                for i in range(n):
                    writer.writerow({"run_id": "synthetic-run", "configuration_id": "synthetic-config", "fold": int(folds[i]),
                                     "row_id": f"syn-{i:04d}", "actual": float(actual[i]), "predicted": float(predicted[i])})
            oof_sha = hashlib.sha256(oof.read_bytes()).hexdigest()
            meta = {"run_id": "synthetic-run", "configuration_id": "synthetic-config", "evaluation_population": "development_oof",
                    "row_count": n, "config_sha256": "a" * 64, "source_sha256": "b" * 64,
                    "development_data_sha256": "c" * 64, "fold_assignment_sha256": "d" * 64,
                    "oof_sha256": oof_sha, "fold_counts": {"0": 390, "1": 389, "2": 389}, "validation_partition_used": False}
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            result = build_development_oof_evaluation(
                oof_path=oof, metadata_path=meta_path, output_root=output, run_id="synthetic-run",
                configuration_id="synthetic-config", config_sha256="a" * 64, source_sha256="b" * 64,
                development_data_sha256="c" * 64, fold_sha256="d" * 64,
                phase4_summary={"fold_results": fold_metrics}, schema_path=schema,
            )
            self.assertEqual(result["row_count"], n)
            self.assertEqual(result["fold_counts"], {"0": 390, "1": 389, "2": 389})
            self.assertEqual(len(result["figures"]), 3)
            validate_document(result["index"], schema)
            self.assertEqual(result["index"]["status"], "PLANNED")
            self.assertTrue(all(item["review_status"] == "AWAITING_REVIEW" for item in result["index"]["evaluations"]))

    def test_oof_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "oof.csv").write_text("wrong", encoding="utf-8")
            (root / "meta.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_development_oof_evaluation(
                    oof_path=root / "oof.csv", metadata_path=root / "meta.json", output_root=root / "out",
                    run_id="run", configuration_id="cfg", config_sha256="a" * 64, source_sha256="b" * 64,
                    development_data_sha256="c" * 64, fold_sha256="d" * 64,
                    phase4_summary={"fold_results": []},
                    schema_path=Path(__file__).resolve().parents[2] / "docs/ui-ux/case-package/phase-05/evaluation-index.schema.json",
                )


if __name__ == "__main__":
    unittest.main()
