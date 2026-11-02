"""Run reproducible Steam Review Multiplier phases in bounded steps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from housing_regression.steam_case_package import build_candidate
from housing_regression.steam_review_multiplier import profile, run_models


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["profile", "models", "package"])
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.phase == "profile":
        result = profile(args.data_dir, args.run_dir, args.repo_root)
    elif args.phase == "models":
        result = run_models(args.data_dir, args.run_dir, args.repo_root)
    else:
        result = build_candidate(args.repo_root, args.run_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
