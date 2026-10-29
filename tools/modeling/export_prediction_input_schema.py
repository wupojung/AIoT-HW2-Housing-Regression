#!/usr/bin/env python3
"""Export prediction-input-schema.json from a digest-verified fitted bundle.

Only deserialize model artifacts from a trusted source after independently
obtaining their expected SHA-256. This tool does not predict or publish models.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

from housing_regression.prediction_input_schema import (  # noqa: E402
    PredictionInputSchemaError,
    build_prediction_input_schema,
    sha256_file,
    write_schema_new,
)


def _read_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PredictionInputSchemaError("could not read run manifest JSON") from exc
    if not isinstance(data, dict):
        raise PredictionInputSchemaError("run manifest root must be an object")
    return data


def _load_verified_bundle(model_path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    if model_path.is_symlink() or not model_path.is_file():
        raise PredictionInputSchemaError("model path must be an existing regular file, not a symlink")
    expected = expected_sha256.lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise PredictionInputSchemaError("expected SHA-256 must contain 64 hexadecimal characters")
    actual = sha256_file(model_path)
    if actual != expected:
        raise PredictionInputSchemaError("model artifact SHA-256 does not match the trusted expected digest")

    # joblib deserialization can execute Python code. Keep this strictly after
    # the caller-provided trusted digest check; never accept uploaded bundles.
    try:
        import joblib

        bundle = joblib.load(model_path)
    except Exception as exc:
        raise PredictionInputSchemaError("could not deserialize the digest-verified model bundle") from exc
    if not isinstance(bundle, dict):
        raise PredictionInputSchemaError("unsupported model bundle format")
    return bundle, actual


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", required=True, type=Path, help="trusted fitted model bundle")
    parser.add_argument("--expected-sha256", required=True, help="trusted digest verified before joblib deserialization")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-version", default=None)
    parser.add_argument("--run-manifest", type=Path, default=None, help="optional trusted JSON run manifest bound to the model digest")
    parser.add_argument("--output", required=True, type=Path, help="new private output path; existing files are never overwritten")
    args = parser.parse_args(argv)

    try:
        if args.output.name != "prediction-input-schema.json":
            raise PredictionInputSchemaError("output filename must be prediction-input-schema.json")
        manifest = _read_manifest(args.run_manifest)
        bundle, model_sha = _load_verified_bundle(args.model_path, args.expected_sha256)
        document = build_prediction_input_schema(
            bundle,
            case_id=args.case_id,
            model_id=args.model_id,
            model_sha256=model_sha,
            model_version=args.model_version,
            run_manifest=manifest,
        )
        output = write_schema_new(args.output, document)
    except (PredictionInputSchemaError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        "exported prediction-input-schema.json: "
        f"{document['input_feature_count']} raw inputs, "
        f"{document['preprocessing_reference']['encoded_feature_count']} encoded, "
        f"{document['preprocessing_reference']['selected_encoded_feature_count']} selected; "
        f"status={document['status']}"
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
