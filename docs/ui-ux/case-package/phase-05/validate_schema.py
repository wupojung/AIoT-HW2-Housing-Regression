#!/usr/bin/env python3
"""Validate Phase 5 JSON samples against the Draft 2020-12 schema.

Run from any working directory:
    python docs/ui-ux/case-package/phase-05/validate_schema.py
Requires: python -m pip install "jsonschema[format]==4.26.0"
This validates JSON structure, NOT cross-file joins or publication authorization.
"""
from pathlib import Path
import json

from jsonschema import Draft202012Validator, FormatChecker

root = Path(__file__).resolve().parent

schema = json.loads(
    (root / "evaluation-index.schema.json").read_text(encoding="utf-8")
)

Draft202012Validator.check_schema(schema)

validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker()
)

samples = [
    "sample/evaluations.json",
    "sample/evaluations.nonempty.mock.json",
]

failed = False

for name in samples:
    data = json.loads((root / name).read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(data), key=lambda e: e.json_path)

    if errors:
        failed = True
        print(f"FAIL: {name}")
        for error in errors:
            print(f"  {error.json_path}: {error.message}")
    else:
        print(f"PASS: {name}")

if failed:
    raise SystemExit(1)
