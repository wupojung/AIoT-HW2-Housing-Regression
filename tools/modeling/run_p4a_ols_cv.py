#!/usr/bin/env python3
"""Run Issue #17 P4-A: all-feature OLS baseline with seed-42 5-fold CV on development rows.

Reads only the labeled train CSV (development-train lines only; holdout lines are skipped
unparsed). Never opens the competition test file.

Output policy:
- --output-dir specifies the directory for public-safe p4a_ols_cv_public.json.
- Private p4a_ols_cv_local.json always goes to the fixed repository ignored path:
  local/research/phase4-p4a/p4a_ols_cv_local.json
- Verifies that the private artifact path is git-ignored using `git check-ignore` before creating
  directories or writing either file. Fails closed immediately if not ignored or on any check error.
- Writes the private local artifact before writing the public summary.

Usage:
    python tools/modeling/run_p4a_ols_cv.py --data-dir <local>/datasets --output-dir <public-or-local-dir>
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

FIXED_PRIVATE_DIR = REPO_ROOT / "local" / "research" / "phase4-p4a"
FIXED_PRIVATE_ARTIFACT_PATH = FIXED_PRIVATE_DIR / "p4a_ols_cv_local.json"


def is_path_git_ignored(path: Path) -> bool:
    """Check if the given path is ignored by git. Fails closed on any error."""
    try:
        res = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return res.returncode == 0
    except Exception as exc:
        raise RuntimeError(f"Failed to execute git check-ignore for {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="P4-A OLS 5-fold CV (development rows only)")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "local" / "datasets")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "local" / "research" / "phase4-p4a")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    public_dir = args.output_dir.resolve()
    private_file = FIXED_PRIVATE_ARTIFACT_PATH.resolve()

    # Pre-flight check: verify private artifact destination is git-ignored before creating dirs or writing
    if not is_path_git_ignored(private_file):
        raise SystemExit(
            f"BLOCKED: private artifact path '{private_file}' is not git-ignored. Failing closed."
        )

    rows, provenance = load_development_rows(args.data_dir / "train.csv", 0.2, args.seed)
    if len(rows) != 1168:
        raise SystemExit(f"BLOCKED: expected 1168 development rows, got {len(rows)}")
    result = run_ols_cv(rows, n_splits=args.folds, random_state=args.seed)

    # 1. Write private artifact first to the fixed ignored path
    FIXED_PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    local = dict(result)
    local["provenance"] = provenance
    private_file.write_text(json.dumps(local, indent=2), encoding="utf-8")
    print(f"Private artifact written: {private_file}")

    # 2. Write public summary second to the requested public output directory
    public_dir.mkdir(parents=True, exist_ok=True)
    public = public_summary(result)
    public["provenance"] = provenance
    public_file = public_dir / "p4a_ols_cv_public.json"
    public_file.write_text(json.dumps(public, indent=2), encoding="utf-8")
    print(f"Public summary written: {public_file}")

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
