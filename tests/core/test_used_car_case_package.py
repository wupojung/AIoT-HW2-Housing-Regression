"""Fail-closed package-builder tests using synthetic identity metadata only."""

import json
import tempfile
import unittest
from pathlib import Path

from housing_regression.used_car_case_package import (
    UsedCarPackageError,
    build_used_car_case_package,
)


class UsedCarCasePackageTests(unittest.TestCase):
    def test_rejects_wrong_run_identity_before_creating_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            run.mkdir()
            (run / "checkpoint.json").write_text(json.dumps({
                "case_id": "used-car-price-optimized",
                "run_id": "not-the-authorized-run",
                "source_sha256": "a" * 64,
            }), encoding="utf-8")
            (run / "config.json").write_text(json.dumps({
                "source_sha256": "a" * 64,
            }), encoding="utf-8")
            destination = root / "package"
            with self.assertRaisesRegex(UsedCarPackageError, "source run identity"):
                build_used_car_case_package(run, destination)
            self.assertFalse(destination.exists())

    def test_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            run.mkdir()
            destination = root / "existing-package"
            destination.mkdir()
            (destination / "owner-evidence.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(UsedCarPackageError, "refusing to overwrite"):
                build_used_car_case_package(run, destination)
            self.assertEqual((destination / "owner-evidence.txt").read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
