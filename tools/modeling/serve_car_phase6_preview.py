#!/usr/bin/env python3
"""Serve an opt-in loopback CAR Phase 6 preview and local prediction API."""

from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))
sys.path.insert(0, str(REPO_ROOT))

from housing_regression.car_phase6_preview_server import create_preview_server, validate_tailnet_origin  # noqa: E402
from housing_regression.local_car_prediction_api import (  # noqa: E402
    PredictionInputSchemaError,
    create_local_server,
    load_verified_car_runtime,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path, help="trusted archived Run 03 directory")
    parser.add_argument("--schema", required=True, type=Path, help="ignored local prediction-input-schema.json")
    parser.add_argument("--tailnet-origin", help="exact HTTPS device.ts.net origin; enables the Tailnet Host route")
    parser.add_argument("--web-port", type=int, default=8788)
    parser.add_argument("--api-port", type=int, default=8789)
    args = parser.parse_args(argv)
    try:
        tailnet_origin = validate_tailnet_origin(args.tailnet_origin)
        runtime = load_verified_car_runtime(args.run_root, args.schema)
        api_origins = [f"http://127.0.0.1:{args.web_port}"]
        if tailnet_origin:
            api_origins.append(tailnet_origin)
        api_server = create_local_server(runtime, args.api_port, allowed_origins=api_origins)
        preview_server = create_preview_server(
            REPO_ROOT / "web", api_port=args.api_port, web_port=args.web_port, tailnet_origin=tailnet_origin
        )
    except (OSError, ValueError, PredictionInputSchemaError) as exc:
        print(f"CAR Phase 6 preview blocked: {exc}", file=sys.stderr)
        return 2

    api_thread = threading.Thread(target=api_server.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True)
    api_thread.start()
    print(f"Local preview: http://127.0.0.1:{args.web_port}/?car-phase6-prototype=1&car-local-inference=1#phase-6", flush=True)
    print(f"Loopback API: 127.0.0.1:{args.api_port} (no external bind)", flush=True)
    if tailnet_origin:
        print(f"Tailnet preview origin enabled: {tailnet_origin}", flush=True)
        print("The browser API path is same-origin /api; no API port is exposed through Serve.", flush=True)
    else:
        print("Tailnet origin is not configured; only the loopback preview origin is accepted.", flush=True)
    print("Prediction values and request bodies are not logged. Stop with Ctrl-C.", flush=True)
    try:
        preview_server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        preview_server.shutdown()
        preview_server.server_close()
        api_server.shutdown()
        api_server.server_close()
        api_thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
