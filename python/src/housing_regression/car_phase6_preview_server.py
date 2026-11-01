"""Loopback-only static Phase 6 preview and same-origin API gateway.

The optional Tailnet origin is an exact local operator setting. Tailscale Serve
must terminate HTTPS and proxy only to this loopback listener; this process
never binds to a network interface other than 127.0.0.1.
"""

from __future__ import annotations

import mimetypes
import re
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from housing_regression.local_car_prediction_api import MAX_REQUEST_BYTES

_ALLOWED_STATIC = frozenset({
    "",
    "index.html",
    "app.js",
    "styles.css",
    "input-contract.js",
    "data/fixtures/car-single-small.json",
    "data/fixtures/car-single-large.json",
    "data/fixtures/car-batch-preview.json",
})
_API_PATHS = frozenset({"/api/health", "/api/schema", "/api/predict"})
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def validate_tailnet_origin(origin: str | None) -> str | None:
    """Require one explicit HTTPS *.ts.net origin; reject paths/wildcards."""
    if origin is None:
        return None
    parsed = urlsplit(origin)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Tailnet preview origin has an invalid port") from exc
    hostname = (parsed.hostname or "").casefold()
    labels = hostname.split(".")
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or port not in {None, 443}
        or parsed.netloc.casefold() not in {hostname, f"{hostname}:443"}
        or len(labels) < 3
        or labels[-2:] != ["ts", "net"]
        or any(not _HOST_LABEL.fullmatch(label) for label in labels)
    ):
        raise ValueError("Tailnet preview origin must be one exact https://<device>.<tailnet>.ts.net origin")
    return f"https://{hostname}"


def make_preview_handler(
    web_root: Path,
    *,
    api_port: int,
    web_port: int,
    tailnet_origin: str | None = None,
):
    root = web_root.resolve(strict=True)
    tailnet_origin = validate_tailnet_origin(tailnet_origin)
    local_origin = f"http://127.0.0.1:{web_port}"
    allowed_origins = {local_origin}
    if tailnet_origin:
        allowed_origins.add(tailnet_origin)

    class Phase6PreviewHandler(BaseHTTPRequestHandler):
        server_version = "RegScopePhase6Preview/1"
        sys_version = ""

        def log_message(self, _format: str, *args: object) -> None:
            # Avoid logging request URLs, form values, or prediction requests.
            return

        def _origin_for_host(self) -> str | None:
            host = self.headers.get("Host", "").casefold()
            for origin in allowed_origins:
                if urlsplit(origin).netloc.casefold() == host:
                    return origin
            return None

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
            if relative not in _ALLOWED_STATIC:
                self._error(404, "not_found")
                return
            if relative == "" or relative == "index.html":
                valid_queries = (
                    {"car-phase6-prototype": ["1"], "car-local-inference": ["1"]},
                    {"car-tailnet-preview": ["1"], "car-local-inference": ["1"]},
                )
                if query not in valid_queries:
                    self._error(404, "not_found")
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
            if expected_origin is None or origin is not None and origin != expected_origin:
                self._error(403, "origin_rejected")
                return
            forwarded_origin = origin or expected_origin
            headers = {"Origin": forwarded_origin, "Accept": "application/json"}
            if self.command == "POST":
                if self.headers.get_content_type() != "application/json":
                    self._error(415, "content_type_required")
                    return
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(body))
            connection = HTTPConnection("127.0.0.1", api_port, timeout=20)
            try:
                connection.request(self.command, request.path, body=body if self.command == "POST" else None, headers=headers)
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
            elif urlsplit(self.path).path.startswith("/api/"):
                self._proxy_api()
            elif self.path == "/" or urlsplit(self.path).path.lstrip("/") in _ALLOWED_STATIC:
                self._serve_static()
            else:
                self._error(404, "not_found")

        def do_POST(self) -> None:  # noqa: N802
            if self._origin_for_host() is None:
                self._error(403, "host_rejected")
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
    tailnet_origin: str | None = None,
) -> ThreadingHTTPServer:
    if not 1 <= web_port <= 65535 or not 1 <= api_port <= 65535 or web_port == api_port:
        raise ValueError("preview and API ports must be distinct valid TCP ports")
    handler = make_preview_handler(web_root, api_port=api_port, web_port=web_port, tailnet_origin=tailnet_origin)
    server = ThreadingHTTPServer(("127.0.0.1", web_port), handler)
    server.daemon_threads = True
    return server
