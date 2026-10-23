#!/usr/bin/env python3
"""Scan staged, tracked, or repository files for common sensitive content."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
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


def _run_git(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def staged_paths() -> list[str]:
    return _run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR")


def tracked_paths() -> list[str]:
    return _run_git("ls-files")


def public_untracked_paths() -> list[str]:
    return _run_git("ls-files", "--others", "--exclude-standard")


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


def _staged_content(path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f":{path}"], cwd=ROOT, check=False, capture_output=True
    )
    return result.stdout if result.returncode == 0 else None


def scan(mode: str) -> list[str]:
    findings: list[str] = []
    if mode == "staged":
        paths = sorted(set(staged_paths()) | set(tracked_paths()))
    elif mode == "tracked":
        paths = tracked_paths()
    else:
        # Git itself applies ignore rules here, so local/ remains usable on disk.
        paths = sorted(set(tracked_paths()) | set(public_untracked_paths()))

    for path in paths:
        if is_forbidden_path(path):
            findings.append(f"{path}: forbidden sensitive/local file path")
            continue
        file_path = ROOT / Path(path)
        content = _staged_content(path) if mode == "staged" else None
        if content is None:
            try:
                content = file_path.read_bytes()
            except (OSError, IsADirectoryError):
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
        except OSError:
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
    findings = scan(mode) if mode else []
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
