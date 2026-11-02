"""Loopback-only static preview and local Steam-model inference endpoint."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from housing_regression.steam_review_multiplier import CASE_ID, MODEL_INPUT_FIELDS, predict_from_inputs

MAX_REQUEST_BYTES = 32 * 1024


def make_handler(repo_root: Path, model_path: Path, model_meta_path: Path):
    root = repo_root.resolve(strict=True)
    model = model_path.resolve(strict=True)
    meta = json.loads(model_meta_path.read_text(encoding="utf-8"))
    if meta.get("case_id") != CASE_ID:
        raise ValueError("private model metadata is not bound to the Steam case")

    class SteamPreviewHandler(BaseHTTPRequestHandler):
        server_version = "RegScopeSteamLocalPreview/1"
        sys_version = ""

        def log_message(self, _format, *args):
            # Do not log submitted game attributes or prediction requests.
            return

        def _json(self, status: int, payload: dict):
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/steam/health":
                self._json(200, {"case_id": CASE_ID, "status": "LOCAL_PRIVATE_VERIFIED",
                                 "model_version": meta["model_version"], "configuration_id": meta["selected_configuration"]})
                return
            if path.startswith("/api/"):
                self._json(404, {"error": {"code": "not_found"}})
                return
            relative = unquote(path).lstrip("/") or "web/index.html"
            candidate = (root / relative).resolve(strict=False)
            if not candidate.is_relative_to(root):
                self._json(404, {"error": {"code": "not_found"}})
                return
            cursor = root
            for part in Path(relative).parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    self._json(404, {"error": {"code": "not_found"}})
                    return
            if candidate.is_dir():
                candidate = candidate / "index.html"
            try:
                resolved = candidate.resolve(strict=True)
                info = resolved.stat()
                if not resolved.is_relative_to(root) or not stat.S_ISREG(info.st_mode) or info.st_size > 8 * 1024 * 1024:
                    raise OSError("invalid static path")
                data = resolved.read_bytes()
            except OSError:
                self._json(404, {"error": {"code": "not_found"}})
                return
            mime = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") or mime == "application/javascript" else ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if urlsplit(self.path).path != "/api/steam/predict":
                self._json(404, {"error": {"code": "not_found"}})
                return
            raw_length = self.headers.get("Content-Length", "")
            if not raw_length.isdigit() or int(raw_length) > MAX_REQUEST_BYTES:
                self._json(413, {"error": {"code": "request_too_large"}})
                return
            try:
                body = self.rfile.read(int(raw_length))
                request = json.loads(body)
                if not isinstance(request, dict) or request.get("case_id") != CASE_ID or not isinstance(request.get("features"), dict):
                    raise ValueError("invalid request shape")
                features = request["features"]
                if set(features) != set(MODEL_INPUT_FIELDS) or not isinstance(features.get("genres"), list):
                    raise ValueError("all model features must be supplied exactly once")
                review_count = request.get("review_count")
                if isinstance(review_count, bool) or not isinstance(review_count, (int, float)) or not 1 <= review_count <= 10_000_000:
                    raise ValueError("review_count must be between 1 and 10000000")
                genre_options = set(json.loads((root / "web/data/candidates/steam-review-multiplier/phases/phase-06/input-schema.json").read_text(encoding="utf-8"))["genre_options"])
                if any(not isinstance(g, str) or g not in genre_options for g in features["genres"]):
                    raise ValueError("unknown genre")
                for key in ["price", "required_age", "dlc_count", "achievements", "release_year", "category_count", "tag_count", "supported_language_count", "full_audio_language_count", "discount", "developer_count", "publisher_count", "screenshot_count", "movie_count"]:
                    value = features[key]
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (-1e6 < value < 1e6):
                        raise ValueError(f"{key} must be a finite numeric value")
                for key in ["windows", "mac", "linux", "has_english", "has_traditional_chinese", "has_website"]:
                    if features[key] not in (0, 1, False, True):
                        raise ValueError(f"{key} must be boolean")
                k = predict_from_inputs(model, features)
                if not (0 <= k < 1e7):
                    raise ValueError("model output outside supported range")
                self._json(200, {"case_id": CASE_ID, "model_version": meta["model_version"],
                                 "configuration_id": meta["selected_configuration"], "predicted_k": k,
                                 "review_count": review_count, "estimated_ownership": k * review_count,
                                 "fixed_k_30_ownership": 30 * review_count,
                                 "model_name": "Random Forest Regressor"})
            except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                self._json(400, {"error": {"code": "invalid_request", "message": str(exc)}})

    return SteamPreviewHandler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("Steam homework preview must bind to loopback")
    model_path = args.run_dir / "private/steam-review-multiplier.joblib"
    metadata_path = args.run_dir / "private/model-metadata.json"
    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.repo_root, model_path, metadata_path))
    print(f"Local Steam homework preview: http://127.0.0.1:{args.port}/web/?steam-homework-preview=1")
    print("Loopback only. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
