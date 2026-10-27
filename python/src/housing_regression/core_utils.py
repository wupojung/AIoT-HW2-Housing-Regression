"""Shared artifact helpers for the G2 phase cores."""

from __future__ import annotations

import json
import os
from pathlib import Path


class PhaseCoreError(ValueError):
    """Raised when a phase core input or output location is invalid."""


def emit_json_artifact(document: dict, output_dir: str | os.PathLike[str], filename: str) -> Path:
    """Write one JSON artifact without overwriting existing evidence."""
    directory = Path(output_dir)
    if directory.is_symlink() or not directory.is_dir():
        raise PhaseCoreError("output_dir must be an existing non-symlink directory")
    destination = directory / filename
    payload = (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    try:
        with destination.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise PhaseCoreError(f"refusing to overwrite existing {filename}") from exc
    except OSError as exc:
        try:
            destination.unlink()
        except OSError:
            pass
        raise PhaseCoreError(f"could not write {filename}") from exc
    return destination
