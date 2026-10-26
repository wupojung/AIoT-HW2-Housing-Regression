#!/usr/bin/env python3
"""Generic JSON Schema validator for any RegScope Phase or Case Package.

Examples (from repository root):
  python docs/design/tools/validate_schema.py \
    --schema docs/ui-ux/case-package/phase-05/evaluation-index.schema.json \
    docs/ui-ux/case-package/phase-05/sample/evaluations.json \
    docs/ui-ux/case-package/phase-05/sample/evaluations.nonempty.mock.json

Requires: python -m pip install "jsonschema[format]==4.26.0"
Only checks JSON Schema, not cross-file references, authorization, release hashes or publication.
"""
import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JSON documents against a Draft 2020-12 schema")
    parser.add_argument("--schema", type=Path, required=True, help="JSON Schema file")
    parser.add_argument("samples", nargs="+", type=Path, help="One or more JSON files to validate")
    args = parser.parse_args()
    try:
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, ValueError, Exception) as exc:
        print(f"FAIL: schema {args.schema}: {exc}", file=sys.stderr)
        return 2

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failed = False
    for path in args.samples:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            errors = sorted(validator.iter_errors(data), key=lambda e: e.json_path)
        except (OSError, ValueError) as exc:
            print(f"FAIL: {path}: {exc}")
            failed = True
            continue
        if errors:
            failed = True
            print(f"FAIL: {path}")
            for error in errors:
                print(f"  {error.json_path}: {error.message}")
        else:
            print(f"PASS: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
