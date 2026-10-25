"""Synthetic tests for Issue #17 P4-A OLS cross-validation (no real CSVs)."""

from __future__ import annotations

import csv
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from sklearn.model_selection import KFold

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.data_prep import AmesDataPreparationPipeline, split_labeled_dataset  # noqa: E402
from housing_regression.modeling import (  # noqa: E402
    compute_numerical_diagnostics,
    development_train_indices,
    fit_ols_svd,
    kfold_assignments,
    load_development_rows,
    run_ols_cv,
)
from housing_regression.modeling.ols_cv import fold_assignment_digest, public_summary  # noqa: E402
from tools.modeling.run_p4a_ols_cv import is_path_git_ignored  # noqa: E402

NEIGHBORHOODS = ["CollgCr", "Veenker", "Crawfor", "NoRidge", "Mitchel"]


def synthetic_rows(n: int, seed: int = 0) -> list[dict[str, str]]:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        area = rng.randint(4000, 15000)
        qual = rng.randint(1, 10)
        nb = NEIGHBORHOODS[i % len(NEIGHBORHOODS)]
        price = 20000 + 8 * area + 15000 * qual + 10000 * NEIGHBORHOODS.index(nb) + rng.gauss(0, 5000)
        rows.append({
            "Id": str(i + 1),
            "LotArea": str(area) if i % 7 else "NA",
            "OverallQual": str(qual),
            "Neighborhood": nb,
            "SalePrice": f"{price:.0f}",
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


class SplitProvenanceTests(unittest.TestCase):
    def test_development_indices_match_phase3_splitter(self):
        rows = [{"Id": str(i)} for i in range(1460)]
        train_rows, _ = split_labeled_dataset(rows, val_fraction=0.2, random_state=42)
        expected = [int(r["Id"]) for r in train_rows]
        self.assertEqual(development_train_indices(1460, 0.2, 42), expected)
        self.assertEqual(len(expected), 1168)

    def test_kfold_canonical_sklearn_regression_and_digest(self):
        """Verify kfold_assignments strictly matches sklearn.model_selection.KFold(shuffle=True, random_state=42)."""
        n_rows = 1168
        n_splits = 5
        seed = 42
        assignments = kfold_assignments(n_rows, n_splits, seed)
        
        # Canonical sklearn reference
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
        expected_assignments = [0] * n_rows
        for k, (_tr, va) in enumerate(kf.split(range(n_rows))):
            for idx in va:
                expected_assignments[idx] = k
                
        self.assertEqual(assignments, expected_assignments)
        
        # Digest check against known reference
        digest = fold_assignment_digest(assignments)
        self.assertTrue(digest.startswith("7c9f1d00"), f"Expected 7c9f1d00... digest, got {digest}")
        self.assertEqual(digest, "7c9f1d00eb74d8a281ba41ed47d5ebbdbffa0513b4bb778b70d1571735ad6463")

    def test_kfold_deterministic_and_balanced(self):
        a = kfold_assignments(1168, 5, 42)
        self.assertEqual(a, kfold_assignments(1168, 5, 42))
        self.assertNotEqual(a, kfold_assignments(1168, 5, 7))
        sizes = [a.count(k) for k in range(5)]
        self.assertEqual(sum(sizes), 1168)
        self.assertLessEqual(max(sizes) - min(sizes), 1)
        self.assertNotEqual(a[:20], sorted(a[:20]), "assignment should be shuffled")


class IsolationTests(unittest.TestCase):
    def test_loader_parses_only_development_lines(self):
        rows = synthetic_rows(1460)
        # Poison every holdout line: if tokenized and used, it would be visible.
        dev = set(development_train_indices(1460))
        for i, r in enumerate(rows):
            if i not in dev:
                r["SalePrice"] = "HOLDOUT_SENTINEL"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "train.csv"
            write_csv(p, rows)
            real_reader = csv.reader
            calls = {"n": 0}

            def counting_reader(*a, **k):
                calls["n"] += 1
                return real_reader(*a, **k)

            with mock.patch("housing_regression.modeling.ols_cv.csv.reader", counting_reader):
                dev_rows, prov = load_development_rows(p)
        self.assertEqual(len(dev_rows), 1168)
        self.assertEqual(calls["n"], 1 + 1168, "only header + development lines may be tokenized")
        self.assertTrue(all(r["SalePrice"] != "HOLDOUT_SENTINEL" for r in dev_rows))
        self.assertEqual([int(r["Id"]) - 1 for r in dev_rows], sorted(dev))
        self.assertEqual(prov["development_rows"], 1168)
        self.assertTrue(prov["id_uniqueness_verified"])
        self.assertEqual(prov["unique_id_count"], 1168)

    def test_loader_validates_id_uniqueness_synthetic(self):
        rows = synthetic_rows(1460)
        # Introduce a duplicate ID among development rows
        dev_indices = development_train_indices(1460)
        rows[dev_indices[1]]["Id"] = rows[dev_indices[0]]["Id"]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "train.csv"
            write_csv(p, rows)
            with self.assertRaises(ValueError) as ctx:
                load_development_rows(p)
            self.assertIn("Duplicate Id detected", str(ctx.exception))

    def test_loader_refuses_test_file_and_wrong_counts(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.csv"
            write_csv(p, synthetic_rows(10))
            with self.assertRaises(ValueError):
                load_development_rows(p)
            q = Path(d) / "train.csv"
            write_csv(q, synthetic_rows(100))
            with self.assertRaises(ValueError):
                load_development_rows(q)

    def test_runner_source_never_references_test_csv_or_holdout_runner(self):
        src = (REPO_ROOT / "tools" / "modeling" / "run_p4a_ols_cv.py").read_text(encoding="utf-8")
        mod = (SRC_DIR / "housing_regression" / "modeling" / "ols_cv.py").read_text(encoding="utf-8")
        for text in (src, mod):
            self.assertNotIn('"test.csv"', text.replace('== "test.csv"', ""))
            self.assertNotIn("run_data_prep", text)
            self.assertNotIn("split_labeled_dataset(", text, "must not materialize holdout rows")

    def test_safe_output_dir_git_ignore_boundary(self):
        self.assertTrue(is_path_git_ignored(REPO_ROOT / "local" / "research" / "test.json"))
        self.assertFalse(is_path_git_ignored(REPO_ROOT / "docs" / "test.json"))


class FoldLocalPreprocessingTests(unittest.TestCase):
    def test_fresh_pipeline_fit_on_training_fold_only(self):
        rows = synthetic_rows(60)
        # Make a category exist only in a single row so some folds never see it in training.
        rows[3]["Neighborhood"] = "Blueste"
        fitted_ids: list[set[str]] = []
        transformed_ids: list[set[str]] = []
        instances: list[AmesDataPreparationPipeline] = []

        class Spy(AmesDataPreparationPipeline):
            def fit(self, r):
                fitted_ids.append({x["Id"] for x in r})
                instances.append(self)
                return super().fit(r)

            def transform(self, r, split_name="unspecified"):
                if "val" in split_name:
                    transformed_ids.append({x["Id"] for x in r})
                return super().transform(r, split_name)

        result = run_ols_cv(rows, 5, 42, pipeline_factory=Spy)
        self.assertEqual(len(instances), 5)
        self.assertEqual(len({id(i) for i in instances}), 5, "fresh preprocessor per fold")
        for tr, va in zip(fitted_ids, transformed_ids):
            self.assertFalse(tr & va, "validation rows must not be used in fit")
            self.assertEqual(len(tr | va), 60)
        # Learned statistics/categories differ by fold; the rare level is absent in exactly one fold.
        has_rare = ["Neighborhood_Blueste" in f["feature_names"] for f in result["folds"]]
        self.assertEqual(has_rare.count(False), 1)
        medians = {i.numeric_impute_values["LotArea"] for i in instances}
        self.assertGreater(len(medians), 1)
        counts = {f["n_features"] for f in result["folds"]}
        self.assertEqual(len(counts), 2, "feature count must not be forced constant")

    def test_xy_separation_all_columns_used_and_timing_summaries(self):
        rows = synthetic_rows(60)
        result = run_ols_cv(rows, 5, 42)
        for f in result["folds"]:
            self.assertNotIn("Id", f["feature_names"])
            self.assertNotIn("SalePrice", f["feature_names"])
            self.assertEqual(f["diagnostics"]["n_params"], f["n_features"] + 1)
            # Verify separate named timing keys per fold
            el = f["elapsed_seconds"]
            self.assertIn("preprocessing", el)
            self.assertIn("model_fit", el)
            self.assertIn("numerical_diagnostics", el)
            self.assertIn("predict_and_evaluate", el)
            for k in el:
                self.assertGreaterEqual(el[k], 0.0)

        # Verify aggregate timing summaries
        agg_t = result["aggregate"]["timing_seconds"]
        for stage in ["preprocessing", "model_fit", "numerical_diagnostics", "predict_and_evaluate", "total_per_fold"]:
            self.assertIn(stage, agg_t)
            self.assertIn("mean", agg_t[stage])
            self.assertIn("std", agg_t[stage])
            self.assertGreaterEqual(agg_t[stage]["mean"], 0.0)

        json.dumps(public_summary(result))  # public summary must be serializable
        self.assertNotIn("_fold_assignments", public_summary(result))


class SolverDiagnosticsTests(unittest.TestCase):
    def test_rank_deficient_full_one_hot_with_intercept(self):
        rng = np.random.default_rng(0)
        n = 50
        cat = rng.integers(0, 3, n)
        onehot = np.eye(3)[cat]
        x = rng.normal(size=n)
        X = np.column_stack([x, onehot])
        y = 3 + 2 * x + onehot @ np.array([1.0, -1.0, 0.5]) + rng.normal(scale=0.01, size=n)
        fit = fit_ols_svd(X, y)
        diag = compute_numerical_diagnostics(fit["design_matrix"])
        self.assertEqual(fit["n_params"], 5)
        self.assertEqual(diag["rank"], 4)
        self.assertEqual(diag["nullity"], 1)
        self.assertIsNone(diag["condition_number_full"])
        self.assertTrue(np.isfinite(diag["condition_number_effective"]))
        self.assertGreater(diag["tolerance"], 0)
        # Predictions match a reference full-rank parametrization despite non-unique coefficients.
        ref = np.linalg.lstsq(np.column_stack([np.ones(n), x, onehot[:, 1:]]), y, rcond=None)[0]
        yhat = np.column_stack([np.ones(n), X]) @ fit["coef"]
        yref = np.column_stack([np.ones(n), x, onehot[:, 1:]]) @ ref
        np.testing.assert_allclose(yhat, yref, atol=1e-8)

    def test_full_rank_recovers_coefficients(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(40, 3))
        y = 1.5 + X @ np.array([2.0, -1.0, 0.5])
        fit = fit_ols_svd(X, y)
        diag = compute_numerical_diagnostics(fit["design_matrix"])
        self.assertEqual(diag["nullity"], 0)
        np.testing.assert_allclose(fit["coef"], [1.5, 2.0, -1.0, 0.5], atol=1e-10)
        self.assertIsNotNone(diag["condition_number_full"])


if __name__ == "__main__":
    unittest.main()
