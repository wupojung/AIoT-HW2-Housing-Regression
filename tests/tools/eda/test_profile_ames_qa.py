"""Independent statistical and boundary checks for the Phase 2 profiler."""

import csv
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools.eda.profile_ames import _iqr_candidates, _numeric_summary, _paired_correlation, _skew, profile_csv, run


class ProfileAmesStatisticalQATests(unittest.TestCase):
    def test_known_numeric_summary_uses_sample_standard_deviation_and_linear_quantiles(self):
        summary = _numeric_summary([1, 2, 3, 4, 5])
        self.assertEqual(summary["count"], 5)
        self.assertEqual(summary["mean"], 3)
        self.assertEqual(summary["std"], math.sqrt(2.5))
        self.assertEqual((summary["min"], summary["25%"], summary["50%"], summary["75%"], summary["max"]),
                         (1, 2, 3, 4, 5))

    def test_population_moment_skew_matches_known_symmetric_and_asymmetric_values(self):
        self.assertAlmostEqual(_skew([-2, -1, 0, 1, 2]), 0.0)
        self.assertAlmostEqual(_skew([0, 0, 1]), 1 / math.sqrt(2))
        self.assertIsNone(_skew([1, 2]))

    def test_pairwise_complete_correlation_and_constant_columns(self):
        self.assertAlmostEqual(_paired_correlation(["1", "2", "", "4"], ["2", "4", "6", "8"]), 1.0)
        self.assertIsNone(_paired_correlation(["3", "3", "3"], ["1", "2", "3"]))
        self.assertIsNone(_paired_correlation(["1"], ["1"]))

    def test_iqr_fences_and_outlier_count_match_known_values(self):
        self.assertEqual(_iqr_candidates([1, 2, 3, 4, 100]),
                         {"lower_fence": -1.0, "upper_fence": 7.0, "count": 1})

    def test_profile_counts_predictors_and_keeps_target_and_identifier_roles_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            csv_path = Path(temp) / "synthetic.csv"
            columns = ["Id", "SalePrice"] + [f"Feature_{i:02d}" for i in range(1, 15)]
            with csv_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(columns)
                writer.writerow([1, 100] + list(range(14)))
                writer.writerow([2, 200] + list(range(14, 28)))
            output = Path(temp) / "out"
            output.mkdir()
            profile = profile_csv(csv_path, output)
            self.assertEqual(profile["predictor_count_excluding_Id_and_target"], 14)
            self.assertEqual(profile["target"]["name"], "SalePrice")
            self.assertEqual(profile["target"]["count"], 2)
            self.assertEqual(profile["target"]["mean"], 150)
            self.assertEqual(profile["target"]["median"], 150)
            self.assertEqual(profile["target"]["min"], 100)
            self.assertEqual(profile["target"]["max"], 200)
            self.assertNotIn("Id", profile["numeric_summary"])
            self.assertNotIn("SalePrice", profile["numeric_correlation_with_target"])
            self.assertAlmostEqual(profile["numeric_correlation_with_target"]["Feature_01"], 1.0)

    def test_statistics_missingness_duplicates_and_constant_column(self):
        with tempfile.TemporaryDirectory() as temp:
            csv_path = Path(temp) / "synthetic.csv"
            csv_path.write_text(
                "Id,SalePrice,Constant,Value\n1,10,7,1\n2,20,7,\n2,20,7,\n",
                encoding="utf-8",
            )
            output = Path(temp) / "out"
            output.mkdir()
            profile = profile_csv(csv_path, output)
            self.assertEqual(profile["missing"]["columns"], {"Value": 2})
            self.assertEqual(profile["duplicate_rows"], 1)
            self.assertFalse(profile["id"]["unique"])
            self.assertEqual(profile["numeric_summary"]["Constant"]["std"], 0)
            self.assertEqual(profile["numeric_anomaly_candidates_iqr"]["Constant"]["count"], 0)

    def test_empty_and_all_missing_numeric_columns_have_explicit_empty_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            empty_path = Path(temp) / "empty.csv"
            empty_path.write_text("Id,SalePrice,Value\n", encoding="utf-8")
            empty_output = Path(temp) / "empty-out"
            empty_output.mkdir()
            empty = profile_csv(empty_path, empty_output)
            self.assertEqual(empty["shape"], {"rows": 0, "columns": 3})
            self.assertEqual(empty["target"]["count"], 0)
            self.assertNotIn("Id", empty["numeric_summary"])
            self.assertFalse((empty_output / "empty_saleprice_distribution.svg").exists())

            missing_path = Path(temp) / "missing.csv"
            missing_path.write_text('Value\n""\n""\n', encoding="utf-8")
            missing_output = Path(temp) / "missing-out"
            missing_output.mkdir()
            missing = profile_csv(missing_path, missing_output)
            self.assertEqual(missing["missing"]["columns"], {"Value": 2})
            self.assertEqual(missing["numeric_summary"]["Value"], {"count": 0})

    def test_target_histogram_is_well_formed_svg_with_fixed_canvas_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            csv_path = Path(temp) / "train.csv"
            csv_path.write_text("Id,SalePrice\n1,100\n2,200\n3,300\n", encoding="utf-8")
            output = Path(temp) / "out"
            output.mkdir()
            profile_csv(csv_path, output)
            svg_path = output / "train_saleprice_distribution.svg"
            root = ET.parse(svg_path).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertEqual((root.attrib["width"], root.attrib["height"]), ("680", "300"))
            self.assertIn("SalePrice distribution (descriptive)", "".join(root.itertext()))

    def test_run_preserves_source_bytes_and_writes_aggregate_outside_dataset_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "local"
            data = local / "datasets"
            data.mkdir(parents=True)
            inputs = {
                "train.csv": "Id,SalePrice,LotArea\n1,100,10\n2,200,20\n",
                "test.csv": "Id,LotArea\n3,30\n",
                "data_description.txt": "LotArea: Lot size\nSalePrice: Target\n",
            }
            for name, content in inputs.items():
                (data / name).write_text(content, encoding="utf-8")
            before = {name: (data / name).read_bytes() for name in inputs}
            output = local / "research" / "profile"
            report = run(data, output, "2026-10-24", True, local_root=local)
            self.assertEqual({name: (data / name).read_bytes() for name in inputs}, before)
            self.assertTrue((output / "profile.json").is_file())
            self.assertTrue((output / "train_saleprice_distribution.svg").is_file())
            self.assertEqual(report["files"][0]["predictor_count_excluding_Id_and_target"], 1)

    @pytest.mark.xfail(reason="Known gap: DictReader silently ignores excess CSV fields; see QA findings.")
    def test_rejects_csv_row_with_more_cells_than_header(self):
        with tempfile.TemporaryDirectory() as temp:
            csv_path = Path(temp) / "malformed.csv"
            csv_path.write_text("Id,SalePrice\n1,100,unexpected\n", encoding="utf-8")
            output = Path(temp) / "out"
            output.mkdir()
            with self.assertRaises(ValueError):
                profile_csv(csv_path, output)


if __name__ == "__main__":
    unittest.main()
