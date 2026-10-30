#!/usr/bin/env python3
"""Serve the pinned CAR Run 03 predictor on loopback for local UI testing only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))
sys.path.insert(0, str(REPO_ROOT))

from housing_regression.local_car_prediction_api import (  # noqa: E402
    CAR_CONFIGURATION_ID,
    CAR_MODEL_ID,
    CAR_RUN_ID,
    PredictionInputSchemaError,
    create_local_server,
    load_verified_car_runtime,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path, help="trusted archived Run 03 root containing private/run-manifest.json")
    parser.add_argument("--schema", required=True, type=Path, help="locally verified prediction-input-schema.json")
    parser.add_argument("--port", type=int, default=8767, help="loopback TCP port; default: 8767")
    args = parser.parse_args(argv)
    try:
        runtime = load_verified_car_runtime(args.run_root, args.schema)
        server = create_local_server(runtime, args.port)
    except (OSError, ValueError, PredictionInputSchemaError) as exc:
        print(f"local CAR API startup blocked: {exc}", file=sys.stderr)
        return 2

    print(
        "RegScope local CAR prediction API ready at http://127.0.0.1:%d "
        "(%s / %s / %s; local experiment only)"
        % (args.port, CAR_RUN_ID, CAR_CONFIGURATION_ID, CAR_MODEL_ID),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("stopping local CAR prediction API", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
