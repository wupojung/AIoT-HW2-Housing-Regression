#!/usr/bin/env python3
"""Serve a local CAR Phase 6 preview with an optional authenticated Tailscale-IP web listener.

The model prediction API always remains bound to loopback.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import secrets
import shutil
import sys
import subprocess
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))
sys.path.insert(0, str(REPO_ROOT))

from housing_regression.car_phase6_preview_server import create_preview_server  # noqa: E402
from housing_regression.local_car_prediction_api import (  # noqa: E402
    PredictionInputSchemaError,
    create_local_server,
    load_verified_car_runtime,
)

TAILSCALE_APP_CLI = Path("/Applications/Tailscale.app/Contents/MacOS/Tailscale")
TAILNET_AUTH_FILE = REPO_ROOT / "local" / "phase6-tailnet-preview" / "auth-token.txt"


def local_tailscale_ipv4_addresses() -> set[str]:
    executable = shutil.which("tailscale") or (str(TAILSCALE_APP_CLI) if TAILSCALE_APP_CLI.is_file() else None)
    if executable is None:
        raise ValueError("Tailscale CLI is unavailable; refusing non-loopback bind")
    try:
        result = subprocess.run([executable, "ip", "-4"], check=True, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("Tailscale CLI could not verify local IPv4 addresses") from exc
    addresses: set[str] = set()
    for line in result.stdout.splitlines():
        candidate = line.strip()
        try:
            parsed = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if isinstance(parsed, ipaddress.IPv4Address):
            addresses.add(str(parsed))
    return addresses


def ensure_tailnet_auth_token(path: Path = TAILNET_AUTH_FILE) -> str:
    local_dir = REPO_ROOT / "local"
    if local_dir.is_symlink():
        raise ValueError("local/ may not be a symlink for authentication storage")
    local_dir.mkdir(exist_ok=True, mode=0o700)
    local_root = local_dir.resolve(strict=True)
    if local_dir.is_symlink() or path.is_symlink() or not path.is_relative_to(local_dir) or not path.resolve(strict=False).is_relative_to(local_root):
        raise ValueError("authentication token must be stored under ignored local/")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink():
        raise ValueError("authentication token directory may not be a symlink")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file():
            raise ValueError("authentication token file is unsafe")
    else:
        token = secrets.token_urlsafe(48)
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(token + "\n")
        path.chmod(0o600)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError("authentication token permissions must be owner-only")
    token = path.read_text(encoding="ascii").strip()
    if len(token) < 48 or any(char.isspace() for char in token):
        raise ValueError("authentication token is malformed")
    return token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path, help="trusted archived Run 03 directory")
    parser.add_argument("--schema", required=True, type=Path, help="ignored local prediction-input-schema.json")
    parser.add_argument("--tailnet-ip", help="explicit Tailscale IPv4 bind address; requires local Tailscale verification and Basic auth")
    parser.add_argument("--web-port", type=int, default=8788)
    parser.add_argument("--api-port", type=int, default=8789)
    args = parser.parse_args(argv)
    try:
        tailscale_addresses = local_tailscale_ipv4_addresses() if args.tailnet_ip else set()
        if args.tailnet_ip and args.tailnet_ip not in tailscale_addresses:
            raise ValueError("requested Tailscale IPv4 is not currently assigned to this device")
        runtime = load_verified_car_runtime(args.run_root, args.schema)
        local_origin = f"http://127.0.0.1:{args.web_port}"
        api_origins = [local_origin]
        api_server = create_local_server(runtime, args.api_port, allowed_origins=api_origins)
        preview_servers = [create_preview_server(REPO_ROOT / "web", api_port=args.api_port, web_port=args.web_port)]
        auth_token = None
        if args.tailnet_ip:
            auth_token = ensure_tailnet_auth_token()
            preview_servers.append(create_preview_server(
                REPO_ROOT / "web", api_port=args.api_port, web_port=args.web_port,
                bind_host=args.tailnet_ip, tailscale_ipv4_addresses=tailscale_addresses, auth_token=auth_token,
            ))
    except (OSError, ValueError, PredictionInputSchemaError) as exc:
        print(f"CAR Phase 6 preview blocked: {exc}", file=sys.stderr)
        return 2

    api_thread = threading.Thread(target=api_server.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True)
    api_thread.start()
    tailnet_thread = None
    print(f"Local preview: http://127.0.0.1:{args.web_port}/?car-phase6-prototype=1&car-local-inference=1#phase-6", flush=True)
    print(f"Loopback API: 127.0.0.1:{args.api_port} (no external bind)", flush=True)
    if args.tailnet_ip:
        tailnet_thread = threading.Thread(target=preview_servers[1].serve_forever, kwargs={"poll_interval": 0.25}, daemon=True)
        tailnet_thread.start()
        print(f"Direct Tailscale IP preview: http://{args.tailnet_ip}:{args.web_port}/", flush=True)
        print(f"CAR Phase 6 inference: http://{args.tailnet_ip}:{args.web_port}/?car-tailnet-preview=1&car-local-inference=1#phase-6", flush=True)
        print(f"Authentication token file: {TAILNET_AUTH_FILE.relative_to(REPO_ROOT)} (ignored, owner-only, never displayed).", flush=True)
        print("Authentication: HTTP Basic username regscope; token remains local unless Owner retrieves it securely.", flush=True)
        print("Tailnet traffic is encrypted by Tailscale; this HTTP route must not be exposed outside the tailnet.", flush=True)
        print("Only the web gateway binds the Tailscale IP; the prediction API stays on loopback.", flush=True)
    else:
        print("Tailnet IP bind is disabled; only loopback preview is available.", flush=True)
    print("Prediction values and request bodies are not logged. Stop with Ctrl-C.", flush=True)
    try:
        preview_servers[0].serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        for preview_server in preview_servers:
            preview_server.shutdown()
            preview_server.server_close()
        if tailnet_thread is not None:
            tailnet_thread.join(timeout=2)
        api_server.shutdown()
        api_server.server_close()
        api_thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
