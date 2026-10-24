#!/usr/bin/env python3
"""Scan staged, tracked, or repository files for common sensitive content."""

from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GIT_TIMEOUT = float(os.getenv("SECURITY_SCAN_GIT_TIMEOUT", "15.0"))

FORBIDDEN_PARTS = {"local", ".vercel", ".next"}
FORBIDDEN_SUFFIXES = {
    ".pdf", ".parquet", ".pkl", ".pickle", ".joblib", ".sqlite", ".db",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".csv", ".tsv", ".xlsx", ".xls",
    ".pem", ".key", ".p12", ".pfx", ".ipynb",
}
FORBIDDEN_NAMES = {".env", "credentials.json", "token.json"}
SAFE_ENV_NAMES = {".env.example"}
SECRET_PATTERNS = (
    ("private key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("generic credential assignment", re.compile(
        rb"(?i)\b(api[_-]?key|access[_-]?token|client[_-]?secret|password)\b[ \t]*[:=][ \t]*['\"]?[^\s'\"]{12,}"
    )),
)


class GitScanError(RuntimeError):
    """Raised when a Git command fails, times out, or produces invalid output."""


def _run_git(
    *args: str,
    cwd: Path = ROOT,
    timeout: float = DEFAULT_GIT_TIMEOUT,
) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitScanError(f"git {' '.join(args)} timed out after {timeout}s") from exc
    except OSError as exc:
        raise GitScanError(f"git {' '.join(args)} failed to execute: {exc}") from exc

    if result.returncode != 0:
        err = result.stderr.strip()
        raise GitScanError(
            f"git {' '.join(args)} failed with exit code {result.returncode}: {err}"
        )
    return [line for line in result.stdout.splitlines() if line]


def _run_git_paths(
    *args: str,
    cwd: Path = ROOT,
    timeout: float = DEFAULT_GIT_TIMEOUT,
) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args, "-z"],
            cwd=cwd,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitScanError(f"git {' '.join(args)} -z timed out after {timeout}s") from exc
    except OSError as exc:
        raise GitScanError(f"git {' '.join(args)} -z failed to execute: {exc}") from exc

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitScanError(
            f"git {' '.join(args)} -z failed with exit code {result.returncode}: {err}"
        )
    raw_parts = result.stdout.split(b"\0")
    return [os.fsdecode(part) for part in raw_parts if part]


def staged_paths(cwd: Path = ROOT, timeout: float = DEFAULT_GIT_TIMEOUT) -> list[str]:
    return _run_git_paths("diff", "--cached", "--name-only", "--diff-filter=ACMR", cwd=cwd, timeout=timeout)


def tracked_paths(cwd: Path = ROOT, timeout: float = DEFAULT_GIT_TIMEOUT) -> list[str]:
    return _run_git_paths("ls-files", cwd=cwd, timeout=timeout)


def public_untracked_paths(cwd: Path = ROOT, timeout: float = DEFAULT_GIT_TIMEOUT) -> list[str]:
    return _run_git_paths("ls-files", "--others", "--exclude-standard", cwd=cwd, timeout=timeout)


def is_forbidden_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    parts = normalized.split("/")
    name = parts[-1]
    if any(part in FORBIDDEN_PARTS for part in parts):
        return True
    if name in SAFE_ENV_NAMES:
        return False
    if name == ".env" or name.startswith(".env."):
        return True
    if (
        name in FORBIDDEN_NAMES
        or (name.startswith("service-account") and name.endswith(".json"))
        or Path(name).suffix.lower() in FORBIDDEN_SUFFIXES
    ):
        return True
    return False


def content_findings(content: bytes) -> list[str]:
    return [label for label, pattern in SECRET_PATTERNS if pattern.search(content)]


def batch_staged_blobs(
    paths: Iterable[str],
    cwd: Path = ROOT,
    timeout: float = DEFAULT_GIT_TIMEOUT,
) -> dict[str, bytes]:
    path_list = list(dict.fromkeys(paths))
    if not path_list:
        return {}

    stdin_bytes = b"".join(b":" + os.fsencode(p) + b"\0" for p in path_list)
    try:
        with subprocess.Popen(
            ["git", "cat-file", "--batch", "-Z"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            try:
                stdout_bytes, stderr_bytes = proc.communicate(input=stdin_bytes, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                proc.kill()
                try:
                    proc.communicate()
                except Exception:
                    pass
                raise GitScanError(f"git cat-file --batch -Z timed out after {timeout}s") from exc

            if proc.returncode != 0:
                err = stderr_bytes.decode("utf-8", errors="replace").strip()
                raise GitScanError(f"git cat-file --batch -Z failed with exit code {proc.returncode}: {err}")
    except OSError as exc:
        raise GitScanError(f"git cat-file --batch -Z failed to execute: {exc}") from exc

    bio = io.BytesIO(stdout_bytes)
    blobs: dict[str, bytes] = {}
    for path in path_list:
        header_bytes = b""
        while True:
            ch = bio.read(1)
            if not ch or ch == b"\0":
                break
            header_bytes += ch

        if not header_bytes:
            raise GitScanError(f"Unexpected end of output from git cat-file for path '{path}'")

        header_str = header_bytes.decode("utf-8", errors="replace").strip()
        if header_str.endswith(" missing"):
            raise GitScanError(f"Staged blob missing for path '{path}': {header_str}")

        parts = header_str.split()
        if len(parts) < 3:
            raise GitScanError(f"Malformed git cat-file header for path '{path}': {header_str}")

        if parts[1] != "blob":
            raise GitScanError(f"Staged object for path '{path}' is not a blob ({parts[1]}): {header_str}")

        try:
            size = int(parts[2])
        except ValueError as exc:
            raise GitScanError(f"Invalid size in git cat-file header for path '{path}': {header_str}") from exc

        content = bio.read(size)
        if len(content) != size:
            raise GitScanError(f"Truncated blob for path '{path}': expected {size} bytes, got {len(content)}")

        trailing = bio.read(1)
        if trailing != b"\0":
            raise GitScanError(f"Missing expected NUL delimiter after blob for path '{path}'")

        blobs[path] = content

    return blobs


def _staged_content(path: str, cwd: Path = ROOT, timeout: float = DEFAULT_GIT_TIMEOUT) -> bytes:
    blobs = batch_staged_blobs([path], cwd=cwd, timeout=timeout)
    return blobs[path]


def scan(mode: str, root: Path = ROOT, timeout: float = DEFAULT_GIT_TIMEOUT) -> list[str]:
    findings: list[str] = []
    try:
        if mode == "staged":
            paths = sorted(set(staged_paths(cwd=root, timeout=timeout)) | set(tracked_paths(cwd=root, timeout=timeout)))
        elif mode == "tracked":
            paths = tracked_paths(cwd=root, timeout=timeout)
        else:
            # Git itself applies ignore rules here, so local/ remains usable on disk.
            paths = sorted(set(tracked_paths(cwd=root, timeout=timeout)) | set(public_untracked_paths(cwd=root, timeout=timeout)))
    except GitScanError as err:
        findings.append(f"Git metadata scan error: {err}")
        return findings

    paths_to_inspect: list[str] = []
    for path in paths:
        if is_forbidden_path(path):
            findings.append(f"{path}: forbidden sensitive/local file path")
        else:
            paths_to_inspect.append(path)

    blobs: dict[str, bytes] = {}
    if mode == "staged" and paths_to_inspect:
        try:
            blobs = batch_staged_blobs(paths_to_inspect, cwd=root, timeout=timeout)
        except GitScanError as err:
            findings.append(f"Git blob scan error: {err}")
            return findings

    for path in paths_to_inspect:
        if mode == "staged":
            content = blobs.get(path)
            if content is None:
                findings.append(f"{path}: staged blob could not be retrieved")
                continue
        else:
            file_path = root / Path(path)
            if file_path.is_dir():
                continue
            try:
                content = file_path.read_bytes()
            except OSError as exc:
                findings.append(f"{path}: failed to read file content ({exc})")
                continue

        for label in content_findings(content):
            findings.append(f"{path}: possible {label}")

    return findings


def scan_build_dir(directory: Path) -> list[str]:
    """Inspect generated artifacts while allowing their normal .vercel/.next container."""
    if not directory.is_dir():
        return [f"{directory}: build output directory does not exist"]
    findings: list[str] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        if is_forbidden_path(relative):
            findings.append(f"{directory / relative}: forbidden sensitive file in build output")
            continue
        try:
            content = path.read_bytes()
        except OSError as exc:
            findings.append(f"{directory / relative}: failed to read build artifact ({exc})")
            continue
        for label in content_findings(content):
            findings.append(f"{directory / relative}: possible {label} in build output")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true", help="scan staged paths and staged blobs")
    group.add_argument("--tracked", action="store_true", help="scan tracked paths and worktree content")
    group.add_argument("--all", action="store_true", help="scan tracked and all current repository files")
    parser.add_argument("--build-dir", type=Path, action="append", default=[], help="also scan generated build output; may be repeated")
    args = parser.parse_args()
    if not (args.staged or args.tracked or args.all or args.build_dir):
        parser.error("choose a repository scan mode or at least one --build-dir")
    mode = "staged" if args.staged else "tracked" if args.tracked else "all" if args.all else None
    try:
        findings = scan(mode) if mode else []
    except GitScanError as err:
        findings = [f"Git scan error: {err}"]
    for build_dir in args.build_dir:
        findings.extend(scan_build_dir(build_dir if build_dir.is_absolute() else ROOT / build_dir))
    if findings:
        print("Sensitive-content scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1
    scanned = mode or "build output"
    print(f"Sensitive-content scan passed ({scanned}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
