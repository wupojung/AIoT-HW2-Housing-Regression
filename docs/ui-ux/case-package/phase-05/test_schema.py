#!/usr/bin/env python3
"""Phase 5 JSON Schema smoke/negative tests. Synthetic fixtures only; NOT a bundle validator."""
import copy
import json
import pathlib
import sys

import jsonschema
from jsonschema import Draft202012Validator, FormatChecker

BASE = pathlib.Path(__file__).resolve().parent
SCHEMA = BASE / "evaluation-index.schema.json"
EMPTY = BASE / "sample/evaluations.json"
NONEMPTY = BASE / "sample/evaluations.nonempty.mock.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    schema = load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    empty, mock = load(EMPTY), load(NONEMPTY)

    def check(label, payload, expected_pass):
        errors = sorted(validator.iter_errors(payload), key=lambda e: repr(list(e.absolute_path)))
        passed = not errors
        print(f"{label}: {'PASS' if passed == expected_pass else 'FAIL'} "
              f"(actual={'VALID' if passed else 'REJECTED'}, expected={'VALID' if expected_pass else 'REJECTED'})")
        if errors and expected_pass:
            for e in errors[:5]:
                print("   ", "/".join(map(str, e.absolute_path)), e.message)
        if passed != expected_pass:
            raise AssertionError(label)

    print("jsonschema=" + jsonschema.__version__ + " draft=2020-12 format_checker=ENABLED")
    check("empty staging", empty, True)
    check("nonempty synthetic", mock, True)
    variant = copy.deepcopy(mock)
    metric = variant["evaluations"][0]["metrics"]["mae"]
    metric.update(value=5.0, status="VERIFIED", reason_code=None, evidence_ref="synthetic-test-marker")
    variant["evaluations"][0]["metrics"]["rmse"].update(
        value=6.0, status="VERIFIED", reason_code=None, evidence_ref="synthetic-test-marker")
    variant["evaluations"][0]["metrics"]["r2"].update(
        value=-0.25, status="VERIFIED", reason_code=None, evidence_ref="synthetic-test-marker")
    variant["evaluations"][0]["fold_summary"]["sample_sd"] = {"mae": 1.0, "rmse": 1.5, "r2": 0.2}
    check("synthetic numeric verified metrics / negative R2", variant, True)

    def negative(name, payload, change):
        example = copy.deepcopy(payload)
        change(example)
        check(name, example, False)

    negative("verified MAE null", variant, lambda x: x["evaluations"][0]["metrics"]["mae"].update(value=None))
    negative("negative MAE", variant, lambda x: x["evaluations"][0]["metrics"]["mae"].update(value=-1))
    negative("negative RMSE", variant, lambda x: x["evaluations"][0]["metrics"]["rmse"].update(value=-1))
    negative("unavailable metric with number", mock, lambda x: x["evaluations"][0]["metrics"]["mae"].update(value=4))
    negative("wrong residual X axis", mock, lambda x: x["evaluations"][1]["figures"][1]["axes"]["x"].update(field="actual"))
    negative("wrong residual sign", mock, lambda x: x["evaluations"][1]["figures"][1].update(residual_sign=None))
    negative("wrong histogram reference line", mock,
             lambda x: x["evaluations"][1]["figures"][2]["axes"].update(reference_line="y_equals_0"))
    negative("interval PASS without method", mock, lambda x: x["evaluations"][0]["interval"]["int_s"].update(status="PASS"))
    negative("root VERIFIED but empty", empty,
             lambda x: x.update(status="VERIFIED", publication_review="APPROVED", release_id="synthetic-release", generated_at="2026-10-27T00:00:00Z"))
    negative("invalid UTC time when VERIFIED", variant,
             lambda x: x.update(status="VERIFIED", publication_review="APPROVED", release_id="synthetic-release", generated_at="not-a-timestamp"))
    print("SCHEMA STRUCTURAL TESTS PASS. Bundle JOIN/rights/hash validation NOT_IMPLEMENTED.")


if __name__ == "__main__":
    main()
