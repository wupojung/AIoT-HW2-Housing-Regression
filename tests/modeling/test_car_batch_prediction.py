from __future__ import annotations

import csv
import io
import json
import unittest
from unittest.mock import patch

from housing_regression.car_batch_prediction import (
    MAX_BATCH_REQUEST_BYTES,
    MAX_BATCH_RESPONSE_BYTES,
    MAX_BATCH_ROWS,
    predict_csv_batch,
)
from housing_regression.local_car_prediction_api import PredictionApiError, validate_inputs


def synthetic_contract():
    numeric_names = ["year", "odometer", "image_count"] + [f"number_{index:02d}" for index in range(11)]
    fields = [
        {"name": name, "data_type": "number", "nullable": False}
        for name in numeric_names
    ]
    fields.append({
        "name": "trim",
        "data_type": "category",
        "nullable": False,
        "options": [{"value": "SYNTHETIC, VALUE\nWITH LINE BREAK"}],
        "unknown_category_behavior": "error",
    })
    return {
        "case_id": "synthetic-car",
        "model_id": "synthetic-model",
        "model_version": "synthetic-v1",
        "source_evidence": {"run_id": "synthetic-run", "configuration_id": "synthetic-config"},
        "input_feature_count": 15,
        "input_features": fields,
    }


def values(category="SYNTHETIC, VALUE\nWITH LINE BREAK"):
    result = {"year": 2018.0, "odometer": 10.0, "image_count": 2.0}
    result.update({f"number_{index:02d}": float(index + 1) for index in range(11)})
    result["trim"] = category
    return result


def make_csv(rows, *, headers=None):
    headers = headers or list(synthetic_contract()["input_features"][i]["name"] for i in range(15))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(name, "") for name in headers])
    return output.getvalue().encode("utf-8")


class SyntheticRuntime:
    def __init__(self):
        self.contract = synthetic_contract()
        self.schema_sha256 = "c" * 64
        self.calls = []

    def predict(self, inputs):
        checked = validate_inputs(self.contract, inputs)
        self.calls.append(checked)
        return {
            "prediction": sum(value for value in checked.values() if isinstance(value, (int, float))),
            "unit": None,
        }


class CarBatchPredictionTests(unittest.TestCase):
    def test_utf8_bom_reordered_headers_quoted_comma_newline_and_single_match(self):
        runtime = SyntheticRuntime()
        record = values()
        headers = list(reversed(list(record)))
        payload = b"\xef\xbb\xbf" + make_csv([record], headers=headers)
        result = predict_csv_batch(runtime, payload)
        expected = runtime.predict(record)
        self.assertEqual(result["total_rows"], 1)
        self.assertEqual(result["valid_rows"], 1)
        self.assertEqual(result["rows"][0]["status"], "SUCCESS")
        self.assertEqual(result["rows"][0]["row_number"], 2)
        self.assertEqual(result["rows"][0]["input"]["trim"], record["trim"])
        self.assertAlmostEqual(result["rows"][0]["prediction"], expected["prediction"], delta=1e-12)
        self.assertEqual(result["schema_sha256"], runtime.schema_sha256)
        self.assertEqual(result["model_version"], runtime.contract["model_version"])

    def test_partial_success_preserves_order_and_reports_ragged_or_invalid_rows(self):
        runtime = SyntheticRuntime()
        good = values()
        bad_number = dict(good, number_00="not-a-number")
        ragged = list(good.values())[:-1]
        payload = make_csv([good, bad_number]) + b",".join(str(value).encode() for value in ragged) + b"\r\n"
        result = predict_csv_batch(runtime, payload)
        self.assertEqual([row["row_number"] for row in result["rows"]], [2, 4, 6])
        self.assertEqual([row["status"] for row in result["rows"]], ["SUCCESS", "ERROR", "ERROR"])
        self.assertEqual(result["rows"][1]["error_code"], "invalid_number")
        self.assertEqual(result["rows"][2]["error_code"], "csv_row_width_mismatch")
        self.assertEqual((result["valid_rows"], result["error_rows"]), (1, 2))
        self.assertEqual(len(runtime.calls), 1)

    def test_negative_prediction_is_preserved_and_counted_with_warning(self):
        runtime = SyntheticRuntime()
        runtime.predict = lambda _inputs: {"prediction": -123.45, "unit": "USD"}
        result = predict_csv_batch(runtime, make_csv([values()]))
        row = result["rows"][0]
        self.assertEqual(row["prediction"], -123.45)
        self.assertEqual(row["prediction_unit"], "USD")
        self.assertEqual(row["status"], "SUCCESS")
        self.assertEqual(row["warning_code"], "negative_prediction")
        self.assertEqual((result["valid_rows"], result["error_rows"]), (1, 0))

    def test_physical_line_numbers_account_for_quoted_multiline_fields(self):
        runtime = SyntheticRuntime()
        result = predict_csv_batch(runtime, make_csv([values(), values()]))
        self.assertEqual([row["row_number"] for row in result["rows"]], [2, 4])
        self.assertEqual(result["columns"][-7:], [
            "row_number", "prediction", "prediction_unit", "prediction_status", "warning_code",
            "error_code", "error_message",
        ])

    def test_all_invalid_rows_make_no_model_calls(self):
        runtime = SyntheticRuntime()
        bad = values(category="UNVERIFIED_CATEGORY")
        result = predict_csv_batch(runtime, make_csv([bad]))
        self.assertEqual((result["valid_rows"], result["error_rows"]), (0, 1))
        self.assertEqual(result["rows"][0]["error_code"], "unknown_category")
        self.assertEqual(runtime.calls, [])

    def test_domain_invalid_row_is_rejected_before_model_call(self):
        runtime = SyntheticRuntime()
        bad = values()
        bad["odometer"] = -1
        result = predict_csv_batch(runtime, make_csv([bad]))
        self.assertEqual(result["rows"][0]["error_code"], "invalid_domain_value")
        self.assertEqual(runtime.calls, [])

    def test_file_level_errors_fail_before_any_inference(self):
        cases = [
            (b"", "empty_csv"),
            (b"\xff", "invalid_csv_encoding"),
            (b'number_00,"unterminated\r\n', "invalid_csv"),
            (b"trim,trim\r\n", "duplicate_csv_headers"),
            (b"trim\r\n", "csv_header_mismatch"),
        ]
        for payload, code in cases:
            with self.subTest(code=code):
                runtime = SyntheticRuntime()
                with self.assertRaises(PredictionApiError) as caught:
                    predict_csv_batch(runtime, payload)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(runtime.calls, [])

    def test_extra_header_is_rejected_before_inference(self):
        runtime = SyntheticRuntime()
        headers = [field["name"] for field in runtime.contract["input_features"]] + ["extra"]
        payload = make_csv([values()], headers=headers)
        with self.assertRaises(PredictionApiError) as caught:
            predict_csv_batch(runtime, payload)
        self.assertEqual(caught.exception.code, "csv_header_mismatch")
        self.assertEqual(runtime.calls, [])

    def test_body_and_row_limits_are_enforced_before_inference(self):
        runtime = SyntheticRuntime()
        with self.assertRaises(PredictionApiError) as caught:
            predict_csv_batch(runtime, b"x" * (MAX_BATCH_REQUEST_BYTES + 1))
        self.assertEqual(caught.exception.code, "request_too_large")
        self.assertEqual(runtime.calls, [])

        rows = [values() for _ in range(MAX_BATCH_ROWS + 1)]
        with self.assertRaises(PredictionApiError) as caught:
            predict_csv_batch(runtime, make_csv(rows))
        self.assertEqual(caught.exception.code, "too_many_rows")
        self.assertEqual(runtime.calls, [])

    def test_exactly_one_hundred_rows_succeeds_and_runtime_is_reused(self):
        runtime = SyntheticRuntime()
        result = predict_csv_batch(runtime, make_csv([values() for _ in range(MAX_BATCH_ROWS)]))
        self.assertEqual(result["total_rows"], MAX_BATCH_ROWS)
        self.assertEqual(result["valid_rows"], MAX_BATCH_ROWS)
        self.assertEqual(len(runtime.calls), MAX_BATCH_ROWS)

    def test_response_limit_is_fail_closed(self):
        runtime = SyntheticRuntime()
        with patch("housing_regression.car_batch_prediction.MAX_BATCH_RESPONSE_BYTES", 16):
            with self.assertRaises(PredictionApiError) as caught:
                predict_csv_batch(runtime, make_csv([values()]))
        self.assertEqual(caught.exception.code, "batch_response_too_large")

    def test_structural_schema_collision_fails_closed(self):
        runtime = SyntheticRuntime()
        runtime.contract["input_features"][0]["name"] = "prediction"
        with self.assertRaises(PredictionApiError) as caught:
            predict_csv_batch(runtime, make_csv([values()]))
        self.assertEqual(caught.exception.code, "schema_unavailable")

    def test_response_does_not_echo_exceptions_or_private_runtime_details(self):
        class FailingRuntime(SyntheticRuntime):
            def predict(self, _inputs):
                raise RuntimeError("synthetic-private-runtime-detail")

        runtime = FailingRuntime()
        result = predict_csv_batch(runtime, make_csv([values()]))
        encoded = json.dumps(result)
        self.assertNotIn("synthetic-private-runtime-detail", encoded)
        self.assertEqual(result["rows"][0]["error_code"], "inference_failed")
        self.assertNotIn("prediction", result["rows"][0]["error_message"])


if __name__ == "__main__":
    unittest.main()
