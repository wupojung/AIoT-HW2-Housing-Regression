"""Small Draft 2020-12 validator for frozen Case Package contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


class ContractValidationError(ValueError):
    """Raised when a document or its selected contract schema is invalid."""


def phase_schema_path(phase: int) -> Path:
    if phase not in (1, 2):
        raise ValueError("G2 only bundles Phase 1 and Phase 2 schemas")
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "docs" / "contracts" / "schemas" / f"phase-0{phase}.schema.json"


def validate_document(document: Any, schema_path: str | Path) -> None:
    """Validate a JSON-compatible value and raise a concise path-aware error."""
    schema_file = Path(schema_path)
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(
            validator.iter_errors(document),
            key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError) as exc:
        raise ContractValidationError("could not load a valid JSON Schema") from exc
    if errors:
        error = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        raise ContractValidationError(f"{location}: {error.message}")
