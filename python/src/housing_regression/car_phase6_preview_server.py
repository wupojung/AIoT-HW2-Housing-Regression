"""Allowlisted Phase 6 web preview and same-origin API gateway.

The web listener defaults to loopback and may optionally bind to one verified
Tailscale IPv4 with application authentication. The prediction API remains
loopback-only.
"""

from __future__ import annotations

import hashlib
import base64
import hmac
import ipaddress
import json
import mimetypes
import os
import re
import stat
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlsplit

from housing_regression.local_car_prediction_api import MAX_REQUEST_BYTES

_ALLOWED_STATIC = frozenset({
    "",
    "index.html",
    "app.js",
    "styles.css",
    "input-contract.js",
    "data/current-release.json",
    "data/fixtures/car-single-small.json",
    "data/fixtures/car-single-large.json",
    "data/fixtures/car-batch-preview.json",
})
_API_PATHS = frozenset({"/api/health", "/api/schema", "/api/predict"})
_PUBLIC_CASE_IDS = frozenset({"ames-full-model-exploration", "used-car-price-optimized"})
_PUBLIC_MIME = {"application/json": ".json", "image/svg+xml": ".svg", "image/png": ".png"}
_MAX_RELEASE_FILE_BYTES = 8 * 1024 * 1024
_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def validate_preview_bind_host(bind_host: str, tailscale_ipv4_addresses=()) -> str:
    """Allow loopback or an explicitly verified Tailscale CGNAT IPv4 only."""
    try:
        address = ipaddress.ip_address(bind_host)
    except ValueError as exc:
        raise ValueError("preview bind host must be an IPv4 address") from exc
    if not isinstance(address, ipaddress.IPv4Address) or str(address) != bind_host:
        raise ValueError("preview bind host must be a canonical IPv4 address")
    if address == ipaddress.IPv4Address("127.0.0.1"):
        return bind_host
    if address not in _TAILSCALE_CGNAT or bind_host not in set(tailscale_ipv4_addresses):
        raise ValueError("non-loopback preview bind must be a verified local Tailscale IPv4 address")
    return bind_host


def _safe_relative_ref(ref: object) -> bool:
    if not isinstance(ref, str) or not ref or "\\" in ref or ref.startswith("/"):
        return False
    path = PurePosixPath(ref)
    return path.as_posix() == ref and all(part not in {"", ".", ".."} for part in path.parts)


def _read_bound_file(data_root: Path, ref: str, expected_sha256: str, expected_bytes: int) -> bytes:
    if not _safe_relative_ref(ref) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or not 0 <= expected_bytes <= _MAX_RELEASE_FILE_BYTES:
        raise ValueError("public release file binding is invalid")
    candidate = data_root
    for part in PurePosixPath(ref).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("public release files may not traverse symlinks")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(data_root) or not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError("public release reference is not a regular file under web/data")
    with resolved.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        named = resolved.lstat()
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(opened, named):
            raise ValueError("public release file changed during verification")
        content = stream.read(_MAX_RELEASE_FILE_BYTES + 1)
    if len(content) != expected_bytes or len(content) > _MAX_RELEASE_FILE_BYTES or hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("public release file does not match its verified digest and size")
    return content


def _load_public_release_assets(web_root: Path) -> tuple[dict[str, tuple[str, int, str]], str, int]:
    """Build a strict web/data allowlist from the current index and bound manifests."""
    data_root = (web_root / "data").resolve(strict=True)
    if (web_root / "data").is_symlink():
        raise ValueError("web/data must not be a symlink")
    index_path = data_root / "current-release.json"
    if index_path.is_symlink() or not index_path.is_file():
        raise ValueError("current public release index is missing or unsafe")
    index_bytes = index_path.read_bytes()
    index_digest = hashlib.sha256(index_bytes).hexdigest()
    if len(index_bytes) > _MAX_RELEASE_FILE_BYTES:
        raise ValueError("current public release index is too large")
    index = json.loads(index_bytes)
    if not isinstance(index, dict) or index.get("schema_version") != "1.0.0" or not isinstance(index.get("cases"), list):
        raise ValueError("current public release index schema is invalid")
    indexed_cases = {case.get("case_id"): case for case in index["cases"] if isinstance(case, dict)}
    if len(indexed_cases) != len(index["cases"]) or set(indexed_cases) != _PUBLIC_CASE_IDS:
        raise ValueError("current release must contain the two expected public research cases")

    bound: dict[str, tuple[str, int, str]] = {
        "data/current-release.json": (index_digest, len(index_bytes), "application/json")
    }
    for case_id in sorted(_PUBLIC_CASE_IDS):
        release_case = indexed_cases[case_id]
        package_ref = release_case.get("package_ref")
        parts = package_ref.split("/") if isinstance(package_ref, str) else []
        if (
            len(parts) != 5 or parts[0] != "releases" or parts[2] != "cases"
            or parts[3] != case_id or parts[4] != "package.json"
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", parts[1])
            or not _safe_relative_ref(package_ref)
        ):
            raise ValueError("public Case Package path does not match the current release layout")
        package_sha = release_case.get("package_sha256")
        package_size = release_case.get("package_bytes")
        if not isinstance(package_size, int) or isinstance(package_size, bool):
            raise ValueError("public Case Package size is invalid")
        package_bytes = _read_bound_file(data_root, package_ref, package_sha, package_size)
        try:
            manifest = json.loads(package_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("public Case Package manifest is invalid JSON") from exc
        if (
            not isinstance(manifest, dict) or manifest.get("case_id") != case_id
            or manifest.get("package_status") != release_case.get("package_status")
            or manifest.get("package_revision") != parts[1]
            or not isinstance(manifest.get("files"), list)
        ):
            raise ValueError("public release index and Case Package manifest disagree")
        package_root = "/".join(parts[:-1])
        bound[f"data/{package_ref}"] = (package_sha, package_size, "application/json")
        seen: set[str] = set()
        for entry in manifest["files"]:
            if not isinstance(entry, dict):
                raise ValueError("public Case Package file entry is invalid")
            ref, digest, size, mime = entry.get("path"), entry.get("sha256"), entry.get("bytes"), entry.get("mime")
            if (
                not _safe_relative_ref(ref) or ref in seen
                or not isinstance(size, int) or isinstance(size, bool) or not 0 <= size <= _MAX_RELEASE_FILE_BYTES
                or not re.fullmatch(r"[0-9a-f]{64}", digest or "")
                or mime not in _PUBLIC_MIME or not ref.endswith(_PUBLIC_MIME[mime])
                or any(part.lower() in {"private", "models", "raw", "rows", "holdout-records", "oof-predictions"} for part in PurePosixPath(ref).parts)
                or PurePosixPath(ref).name == "prediction-input-schema.json"
            ):
                raise ValueError("public Case Package contains an unsafe or unsupported file reference")
            seen.add(ref)
            bound[f"data/{package_root}/{ref}"] = (digest, size, mime)
    return bound, index_digest, len(index_bytes)


def make_preview_handler(
    web_root: Path,
    *,
    api_port: int,
    web_port: int,
    bind_host: str = "127.0.0.1",
    auth_token: str | None = None,
):
    root = web_root.resolve(strict=True)
    if auth_token is not None and len(auth_token) < 32:
        raise ValueError("preview authentication token must contain at least 32 characters")
    if bind_host != "127.0.0.1" and not auth_token:
        raise ValueError("non-loopback preview bind requires application authentication")
    release_assets, _, _ = _load_public_release_assets(root)
    data_root = (root / "data").resolve(strict=True)
    local_origin = f"http://127.0.0.1:{web_port}"
    bound_origin = f"http://{bind_host}:{web_port}"
    expected_netloc = f"{bind_host}:{web_port}".casefold()

    class Phase6PreviewHandler(BaseHTTPRequestHandler):
        server_version = "RegScopePhase6Preview/1"
        sys_version = ""

        def log_message(self, _format: str, *args: object) -> None:
            # Avoid logging request URLs, form values, or prediction requests.
            return

        def _origin_for_host(self) -> str | None:
            host = self.headers.get("Host", "").casefold()
            return bound_origin if host == expected_netloc else None

        def _authorized(self) -> bool:
            if auth_token is None:
                return True
            expected = "Basic " + base64.b64encode(f"regscope:{auth_token}".encode("utf-8")).decode("ascii")
            supplied = self.headers.get("Authorization", "")
            return hmac.compare_digest(supplied, expected)

        def _unauthorized(self) -> None:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="RegScope local preview", charset="UTF-8"')
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()

        def _error(self, status: int, code: str) -> None:
            payload = ("{\"error\":{\"code\":\"" + code + "\"}}").encode("ascii")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def _serve_static(self) -> None:
            request = urlsplit(self.path)
            query = parse_qs(request.query, keep_blank_values=True) if request.query else {}
            if request.fragment:
                self._error(404, "not_found")
                return
            relative = request.path.lstrip("/")
            if relative in _ALLOWED_STATIC and relative.startswith("data/fixtures/"):
                if (
                    bound_origin != local_origin or self._origin_for_host() != local_origin
                    or query != {"car-phase6-prototype": ["1"], "car-local-inference": ["1"]}
                ):
                    self._error(404, "not_found")
                    return
                candidate = root / relative
                if candidate.is_symlink() or not candidate.resolve(strict=False).is_relative_to(root):
                    self._error(404, "not_found")
                    return
                try:
                    data = candidate.read_bytes()
                except OSError:
                    self._error(404, "not_found")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(data)
                return
            if relative.startswith("data/"):
                binding = release_assets.get(relative)
                if binding is None:
                    self._error(404, "not_found")
                    return
                try:
                    data = _read_bound_file(data_root, relative[5:], binding[0], binding[1])
                except (OSError, ValueError):
                    self._error(502, "public_asset_integrity_failed")
                    return
                mime = binding[2]
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(data)
                return
            if relative not in _ALLOWED_STATIC:
                self._error(404, "not_found")
                return
            if relative == "" or relative == "index.html":
                valid_queries = (
                    {"car-phase6-prototype": ["1"], "car-local-inference": ["1"]},
                    {"car-tailnet-preview": ["1"], "car-local-inference": ["1"]},
                )
                if query and query not in valid_queries:
                    self._error(404, "not_found")
                    return
                requested_origin = self._origin_for_host()
                if query == valid_queries[0] and requested_origin != local_origin:
                    self._error(403, "origin_rejected")
                    return
                if query == valid_queries[1] and (bind_host == "127.0.0.1" or requested_origin != bound_origin):
                    self._error(403, "origin_rejected")
                    return
            elif query:
                self._error(404, "not_found")
                return
            file_name = "index.html" if relative == "" else relative
            candidate = root / file_name
            if candidate.is_symlink():
                self._error(404, "not_found")
                return
            path = candidate.resolve(strict=False)
            if not path.is_relative_to(root) or not path.is_file():
                self._error(404, "not_found")
                return
            try:
                data = path.read_bytes()
            except OSError:
                self._error(404, "not_found")
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(data)

        def _proxy_api(self, *, body: bytes = b"") -> None:
            request = urlsplit(self.path)
            if request.query or request.fragment or request.path not in _API_PATHS:
                self._error(404, "not_found")
                return
            origin = self.headers.get("Origin")
            expected_origin = self._origin_for_host()
            if expected_origin is None or origin is not None and origin != expected_origin or self.command == "POST" and origin != expected_origin:
                self._error(403, "origin_rejected")
                return
            # The backend only accepts loopback Origins. This gateway has
            # already authenticated the client and checked its exact Origin.
            forwarded_origin = local_origin
            headers = {"Origin": forwarded_origin, "Accept": "application/json"}
            if self.command == "POST":
                if self.headers.get_content_type() != "application/json":
                    self._error(415, "content_type_required")
                    return
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(body))
            connection = HTTPConnection("127.0.0.1", api_port, timeout=20)
            try:
                upstream_path = "/health" if request.path == "/api/health" else request.path
                connection.request(self.command, upstream_path, body=body if self.command == "POST" else None, headers=headers)
                response = connection.getresponse()
                payload = response.read(MAX_REQUEST_BYTES + 8192)
                if len(payload) > MAX_REQUEST_BYTES + 8192:
                    self._error(502, "upstream_response_too_large")
                    return
                self.send_response(response.status)
                allowed_headers = {"content-type", "cache-control", "x-content-type-options", "x-schema-sha256", "vary"}
                for key, value in response.getheaders():
                    if key.lower() in allowed_headers:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)
            except OSError:
                self._error(503, "local_api_unavailable")
            finally:
                connection.close()

        def do_GET(self) -> None:  # noqa: N802
            if self._origin_for_host() is None:
                self._error(403, "host_rejected")
            elif not self._authorized():
                self._unauthorized()
            elif urlsplit(self.path).path.startswith("/api/"):
                self._proxy_api()
            elif self.path == "/" or urlsplit(self.path).path.lstrip("/") in _ALLOWED_STATIC or urlsplit(self.path).path.startswith("/data/"):
                self._serve_static()
            else:
                self._error(404, "not_found")

        def do_POST(self) -> None:  # noqa: N802
            if self._origin_for_host() is None:
                self._error(403, "host_rejected")
                return
            if not self._authorized():
                self._unauthorized()
                return
            if self.path != "/api/predict":
                self._error(404, "not_found")
                return
            length_text = self.headers.get("Content-Length", "")
            if not length_text.isdigit() or not 1 <= int(length_text) <= MAX_REQUEST_BYTES:
                self._error(413, "invalid_request_size")
                return
            if self.headers.get("Transfer-Encoding"):
                self._error(400, "transfer_encoding_rejected")
                return
            body = self.rfile.read(int(length_text))
            self._proxy_api(body=body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            if self.path != "/api/predict" or self._origin_for_host() is None:
                self._error(403, "origin_or_route_rejected")
                return
            if not self._authorized():
                self._unauthorized()
                return
            origin = self.headers.get("Origin")
            if origin != self._origin_for_host():
                self._error(403, "origin_rejected")
                return
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")
            self.end_headers()

    return Phase6PreviewHandler


def create_preview_server(
    web_root: Path,
    *,
    api_port: int,
    web_port: int,
    bind_host: str = "127.0.0.1",
    tailscale_ipv4_addresses=(),
    auth_token: str | None = None,
) -> ThreadingHTTPServer:
    if not 1 <= web_port <= 65535 or not 1 <= api_port <= 65535 or web_port == api_port:
        raise ValueError("preview and API ports must be distinct valid TCP ports")
    bind_host = validate_preview_bind_host(bind_host, tailscale_ipv4_addresses)
    handler = make_preview_handler(web_root, api_port=api_port, web_port=web_port, bind_host=bind_host, auth_token=auth_token)
    server = ThreadingHTTPServer((bind_host, web_port), handler)
    server.daemon_threads = True
    return server
