import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python" / "src"))

from housing_regression.init_config import ConfigError, initialize_case, load_config


class InitConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.case_dir = self.root / "case"
        self.case_dir.mkdir()
        self.csv_path = self.root / "synthetic.csv"
        self.csv_bytes = b"LotArea,Neighborhood,SalePrice\n1000,A,120000\n1500,B,180000\n"
        self.csv_path.write_bytes(self.csv_bytes)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_reload_tracks_stable_source_and_config_hashes(self):
        result = initialize_case(self.csv_path, "synthetic-housing", "SalePrice", self.case_dir)
        loaded = load_config(result.config_path)

        self.assertTrue(result.sample_path.is_file())
        self.assertEqual(result.source_sha256, hashlib.sha256(self.csv_bytes).hexdigest())
        self.assertEqual(loaded.source_sha256, result.source_sha256)
        self.assertEqual(loaded.config_sha256, result.config_sha256)
        self.assertEqual(loaded.values["case_id"], "synthetic-housing")
        self.assertEqual(loaded.values["data"]["target"], "SalePrice")
        self.assertFalse(Path(loaded.values["data"]["path"]).is_absolute())
        self.assertIn("later phases read it", result.sample_path.read_text(encoding="utf-8"))

    def test_refuses_to_overwrite_either_config_artifact(self):
        first = initialize_case(self.csv_path, "synthetic-housing", "SalePrice", self.case_dir)
        original = first.config_path.read_bytes()
        with self.assertRaisesRegex(ConfigError, "overwrite"):
            initialize_case(self.csv_path, "synthetic-housing", "SalePrice", self.case_dir)
        self.assertEqual(first.config_path.read_bytes(), original)

        other_case = self.root / "sample-only"
        other_case.mkdir()
        (other_case / "config.sample.yaml").write_text("preserve me", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "overwrite"):
            initialize_case(self.csv_path, "sample-only", "SalePrice", other_case)
        self.assertEqual((other_case / "config.sample.yaml").read_text(encoding="utf-8"), "preserve me")
        self.assertFalse((other_case / "config.yaml").exists())

    def test_rejects_invalid_case_target_and_unsafe_csv_inputs(self):
        for case_id in ("../escape", "MixedCase", "bad/name"):
            with self.subTest(case_id=case_id), self.assertRaises(ConfigError):
                initialize_case(self.csv_path, case_id, "SalePrice", self.case_dir)
        with self.assertRaisesRegex(ConfigError, "absent"):
            initialize_case(self.csv_path, "valid-case", "MissingTarget", self.case_dir)

        duplicate = self.root / "duplicate.csv"
        duplicate.write_text("a,a,SalePrice\n1,2,3\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "unique"):
            initialize_case(duplicate, "valid-case", "SalePrice", self.case_dir)

        directory = self.root / "not-a-csv"
        directory.mkdir()
        with self.assertRaises(ConfigError):
            initialize_case(directory, "valid-case", "SalePrice", self.case_dir)

        source_link = self.root / "source-link.csv"
        source_link.symlink_to(self.csv_path)
        with self.assertRaisesRegex(ConfigError, "symbolic link"):
            initialize_case(source_link, "valid-case", "SalePrice", self.case_dir)

        case_link = self.root / "case-link"
        case_link.symlink_to(self.case_dir, target_is_directory=True)
        with self.assertRaisesRegex(ConfigError, "case_dir"):
            initialize_case(self.csv_path, "valid-case", "SalePrice", case_link)

    def test_rejects_invalid_saved_parameters_and_changed_source(self):
        result = initialize_case(self.csv_path, "synthetic-housing", "SalePrice", self.case_dir)
        config = yaml.safe_load(result.config_path.read_text(encoding="utf-8"))
        config["cross_validation"]["folds"] = 1
        result.config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "at least 2"):
            load_config(result.config_path)

        config["cross_validation"]["folds"] = 5
        config["seed"] = 43
        result.config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "config SHA-256"):
            load_config(result.config_path)

        config["seed"] = 42
        result.config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        self.csv_path.write_bytes(self.csv_bytes + b"2000,C,210000\n")
        with self.assertRaisesRegex(ConfigError, "SHA-256"):
            load_config(result.config_path)


if __name__ == "__main__":
    unittest.main()
