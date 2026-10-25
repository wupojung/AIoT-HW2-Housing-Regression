#!/usr/bin/env python3
"""Run Issue #17 P4-A: all-feature OLS baseline with seed-42 5-fold CV on development rows.

Reads only the labeled train CSV (development-train lines only; holdout lines are skipped
unparsed). Never opens the competition test file. Writes outputs to ignored local/:
- p4a_ols_cv_public.json: public-safe aggregate/fold metrics and diagnostics (no rows, no paths)
- p4a_ols_cv_local.json: adds full singular spectra and fold assignments (local only)

Usage:
    python tools/modeling/run_p4a_ols_cv.py --data-dir <local>/datasets --output-dir <local>/research/phase4-p4a
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "python" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from housing_regression.modeling import load_development_rows, run_ols_cv  # noqa: E402
from housing_regression.modeling.ols_cv import public_summary  # noqa: E402


def is_path_git_ignored(path: Path) -> bool:
    """Check if the given path is ignored by git."""
    try:
        res = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0
    except Exception:
        # Fallback check if git is not accessible: check if under local/
        try:
            path.resolve().relative_to((REPO_ROOT / "local").resolve())
            return True
        except ValueError:
            return False


def main() -> int:
    parser = argparse.ArgumentParser(description="P4-A OLS 5-fold CV (development rows only)")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "local" / "datasets")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "local" / "research" / "phase4-p4a")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, provenance = load_development_rows(args.data_dir / "train.csv", 0.2, args.seed)
    if len(rows) != 1168:
        raise SystemExit(f"BLOCKED: expected 1168 development rows, got {len(rows)}")
    result = run_ols_cv(rows, n_splits=args.folds, random_state=args.seed)

    public = public_summary(result)
    public["provenance"] = provenance
    (out_dir / "p4a_ols_cv_public.json").write_text(json.dumps(public, indent=2), encoding="utf-8")

    # Guard private local artifact against being written outside ignored local/
    if is_path_git_ignored(out_dir / "p4a_ols_cv_local.json"):
        local = dict(result)
        local["provenance"] = provenance
        (out_dir / "p4a_ols_cv_local.json").write_text(json.dumps(local, indent=2), encoding="utf-8")
    else:
        # Enforce writing private details exclusively to verified ignored local directory
        secure_local_dir = REPO_ROOT / "local" / "research" / "phase4-p4a"
        secure_local_dir.mkdir(parents=True, exist_ok=True)
        local = dict(result)
        local["provenance"] = provenance
        (secure_local_dir / "p4a_ols_cv_local.json").write_text(json.dumps(local, indent=2), encoding="utf-8")
        print(
            f"Notice: --output-dir ({out_dir}) is not git-ignored. "
            f"Public summary saved to --output-dir; private local artifact routed securely to {secure_local_dir}."
        )

    agg = result["aggregate"]
    print(f"development rows: {len(rows)}; folds: {result['cv']['fold_sizes']}")
    for f in result["folds"]:
        d = f["diagnostics"]
        print(
            f"fold {f['fold']}: features={f['n_features']} rank={d['rank']} nullity={d['nullity']} "
            f"RMSE={f['rmse_validation']:.1f} R2={f['r2_validation']:.4f}"
        )
    print(
        f"mean RMSE={agg['rmse_validation']['mean']:.1f} (sd {agg['rmse_validation']['std']:.1f}); "
        f"mean R2={agg['r2_validation']['mean']:.4f} (sd {agg['r2_validation']['std']:.4f})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
