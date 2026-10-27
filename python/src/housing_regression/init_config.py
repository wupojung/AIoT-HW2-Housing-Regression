"""Create and validate the immutable-by-default INIT configuration."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any

import yaml


CONFIG_FILENAME = "config.yaml"
SAMPLE_FILENAME = "config.sample.yaml"
CONFIG_VERSION = 1
_CASE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_TARGET = re.compile(r"^[A-Za-z_][A-Za-z0-9_ ]{0,127}$")

DEFAULT_CONFIG: dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "case_id": None,
    "data": {"path": None, "target": None, "sha256": None},
    "seed": 42,
    "cross_validation": {"folds": 5},
    "feature_selection": {"k_values": [5, 10, 20]},
    "models": {
        "enabled": ["pearson", "mutual_info", "ridge_rfe", "lasso", "elastic_net", "ols"],
        "alpha_values": [0.01, 0.1, 1.0, 10.0],
        "l1_ratio_values": [0.25, 0.5, 0.75],
    },
    "provenance": {"config_sha256": None},
}

SAMPLE_CONFIG = """# RegScope INIT configuration template.
# Edit config.yaml when needed; later phases read it and never regenerate it.
config_version: 1
case_id: example-housing
data:
  path: ../data/housing.csv  # Relative to this config file; keep private inputs local.
  target: SalePrice          # Target column; it is never used as a feature.
  sha256: <computed-by-init>
seed: 42                      # Reproducibility seed.
cross_validation:
  folds: 5                    # Number of development CV folds.
feature_selection:
  k_values: [5, 10, 20]      # Candidate feature counts for fixed-K methods.
models:
  enabled: [pearson, mutual_info, ridge_rfe, lasso, elastic_net, ols]
  alpha_values: [0.01, 0.1, 1.0, 10.0]  # Regularization candidates.
  l1_ratio_values: [0.25, 0.5, 0.75]   # Elastic Net mixing candidates.
provenance:
  config_sha256: <computed-by-init>  # Hash of canonical config content without this field.
"""


@dataclass(frozen=True)
class InitResult:
    case_dir: Path
    config_path: Path
    sample_path: Path
    source_sha256: str
    config_sha256: str


@dataclass(frozen=True)
class LoadedConfig:
    values: dict[str, Any]
    config_sha256: str
    source_sha256: str


class ConfigError(ValueError):
    """Raised when INIT inputs or a saved config are unsafe or invalid."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _config_sha256(values: dict[str, Any]) -> str:
    """Hash canonical config content with the self-referential digest omitted."""
    canonical = dict(values)
    canonical_provenance = dict(values["provenance"])
    canonical_provenance.pop("config_sha256", None)
    canonical["provenance"] = canonical_provenance
    content = yaml.safe_dump(canonical, sort_keys=False, allow_unicode=False).encode("utf-8")
    return _sha256(content)


def _read_source(path: Path, target: str) -> tuple[bytes, str]:
    try:
        if path.is_symlink():
            raise ConfigError("CSV path must not be a symbolic link")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ConfigError("CSV path must be a regular file")
        content = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read CSV input: {exc.strerror or exc}") from exc
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ConfigError("CSV input must be UTF-8 encoded") from exc
    try:
        header = next(csv.reader(io.StringIO(text, newline="")))
    except (StopIteration, csv.Error) as exc:
        raise ConfigError("CSV input must contain a valid header row") from exc
    if not header or any(not column.strip() for column in header):
        raise ConfigError("CSV header must contain non-empty column names")
    if len(set(header)) != len(header):
        raise ConfigError("CSV header column names must be unique")
    if target not in header:
        raise ConfigError(f"target column {target!r} is absent from the CSV header")
    return content, _sha256(content)


def _validate_values(values: Any) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise ConfigError("config must be a YAML mapping")
    required = set(DEFAULT_CONFIG)
    if set(values) != required:
        raise ConfigError("config has missing or unexpected top-level fields")
    if type(values["config_version"]) is not int or values["config_version"] != CONFIG_VERSION:
        raise ConfigError("config_version must be 1")
    case_id = values["case_id"]
    if not isinstance(case_id, str) or not _CASE_ID.fullmatch(case_id):
        raise ConfigError("case_id must be lowercase letters, digits, and internal hyphens")
    data = values["data"]
    if not isinstance(data, dict) or set(data) != {"path", "target", "sha256"}:
        raise ConfigError("data must contain exactly path, target, and sha256")
    source_path = data["path"]
    if (not isinstance(source_path, str) or not source_path or Path(source_path).is_absolute()
            or PureWindowsPath(source_path).is_absolute() or PureWindowsPath(source_path).drive):
        raise ConfigError("data.path must be a non-empty relative path")
    if "\\" in source_path or "\x00" in source_path:
        raise ConfigError("data.path must use a safe relative POSIX path")
    if not isinstance(data["target"], str) or not _TARGET.fullmatch(data["target"]):
        raise ConfigError("data.target must be a valid CSV column name")
    digest = data["sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ConfigError("data.sha256 must be a lowercase SHA-256 digest")
    if type(values["seed"]) is not int or values["seed"] < 0:
        raise ConfigError("seed must be a non-negative integer")
    cv = values["cross_validation"]
    if not isinstance(cv, dict) or set(cv) != {"folds"}:
        raise ConfigError("cross_validation must contain exactly folds")
    if type(cv["folds"]) is not int or cv["folds"] < 2:
        raise ConfigError("cross_validation.folds must be an integer of at least 2")
    selection = values["feature_selection"]
    if not isinstance(selection, dict) or set(selection) != {"k_values"}:
        raise ConfigError("feature_selection must contain exactly k_values")
    ks = selection["k_values"]
    if not isinstance(ks, list) or not ks or any(type(k) is not int or k < 1 for k in ks):
        raise ConfigError("feature_selection.k_values must be a non-empty list of positive integers")
    if len(set(ks)) != len(ks):
        raise ConfigError("feature_selection.k_values must not contain duplicates")
    models = values["models"]
    if not isinstance(models, dict) or set(models) != {"enabled", "alpha_values", "l1_ratio_values"}:
        raise ConfigError("models must contain enabled, alpha_values, and l1_ratio_values")
    allowed = {"pearson", "mutual_info", "ridge_rfe", "lasso", "elastic_net", "ols"}
    enabled = models["enabled"]
    if (not isinstance(enabled, list) or not enabled or
            any(not isinstance(name, str) or name not in allowed for name in enabled) or
            len(set(enabled)) != len(enabled)):
        raise ConfigError("models.enabled must be a non-empty list of unique supported methods")
    for field in ("alpha_values", "l1_ratio_values"):
        candidates = models[field]
        if (not isinstance(candidates, list) or not candidates or
                any(type(value) not in (int, float) or not math.isfinite(value) for value in candidates)):
            raise ConfigError(f"models.{field} must be a non-empty list of numbers")
        if field == "alpha_values" and any(value <= 0 for value in candidates):
            raise ConfigError("models.alpha_values must contain positive values")
        if field == "l1_ratio_values" and any(not 0 < value <= 1 for value in candidates):
            raise ConfigError("models.l1_ratio_values must be greater than 0 and at most 1")
    provenance = values["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"config_sha256"}:
        raise ConfigError("provenance must contain exactly config_sha256")
    if not isinstance(provenance["config_sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", provenance["config_sha256"]):
        raise ConfigError("provenance.config_sha256 must be a lowercase SHA-256 digest")
    return values


def initialize_case(data_csv: str | os.PathLike[str], case_id: str, target: str,
                    case_dir: str | os.PathLike[str]) -> InitResult:
    """Create config.yaml and config.sample.yaml once for a synthetic/research case."""
    if not isinstance(case_id, str) or not _CASE_ID.fullmatch(case_id):
        raise ConfigError("case_id must be lowercase letters, digits, and internal hyphens")
    if not isinstance(target, str) or not _TARGET.fullmatch(target):
        raise ConfigError("target must be a valid CSV column name")
    output_dir = Path(case_dir)
    try:
        if output_dir.is_symlink() or not output_dir.is_dir():
            raise ConfigError("case_dir must be an existing directory and not a symbolic link")
        source_path = Path(data_csv).expanduser()
        if source_path.is_symlink():
            raise ConfigError("CSV path must not be a symbolic link")
        source_path = source_path.resolve(strict=True)
        config_path = output_dir / CONFIG_FILENAME
        sample_path = output_dir / SAMPLE_FILENAME
        if config_path.exists() or config_path.is_symlink() or sample_path.exists() or sample_path.is_symlink():
            raise ConfigError("refusing to overwrite existing config evidence")
        _, source_sha = _read_source(source_path, target)
        try:
            relative_source = Path(os.path.relpath(source_path, output_dir.resolve())).as_posix()
        except ValueError as exc:
            raise ConfigError("CSV input and case directory must be on the same filesystem volume") from exc
        values = {
            **DEFAULT_CONFIG,
            "case_id": case_id,
            "data": {"path": relative_source, "target": target, "sha256": source_sha},
            "cross_validation": dict(DEFAULT_CONFIG["cross_validation"]),
            "feature_selection": {"k_values": list(DEFAULT_CONFIG["feature_selection"]["k_values"])},
            "models": {
                "enabled": list(DEFAULT_CONFIG["models"]["enabled"]),
                "alpha_values": list(DEFAULT_CONFIG["models"]["alpha_values"]),
                "l1_ratio_values": list(DEFAULT_CONFIG["models"]["l1_ratio_values"]),
            },
            "provenance": {"config_sha256": ""},
        }
        values["provenance"]["config_sha256"] = _config_sha256(values)
        _validate_values(values)
        serialized = yaml.safe_dump(values, sort_keys=False, allow_unicode=False).encode("utf-8")
        sample_bytes = SAMPLE_CONFIG.encode("utf-8")
        created: list[Path] = []
        try:
            for path, payload in ((config_path, serialized), (sample_path, sample_bytes)):
                with path.open("xb") as stream:
                    created.append(path)
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
        except OSError as exc:
            for path in created:
                try:
                    path.unlink()
                except OSError:
                    pass
            raise ConfigError(f"could not create config evidence: {exc.strerror or exc}") from exc
        return InitResult(output_dir, config_path, sample_path, source_sha,
                          values["provenance"]["config_sha256"])
    except OSError as exc:
        raise ConfigError(f"unsafe or unavailable INIT path: {exc.strerror or exc}") from exc


def load_config(config_path: str | os.PathLike[str]) -> LoadedConfig:
    """Load, validate, and verify source provenance without modifying config."""
    path = Path(config_path)
    try:
        if path.is_symlink() or not path.is_file():
            raise ConfigError("config path must be a regular file and not a symbolic link")
        serialized = path.read_bytes()
        values = _validate_values(yaml.safe_load(serialized.decode("utf-8")))
        config_sha = _config_sha256(values)
        if config_sha != values["provenance"]["config_sha256"]:
            raise ConfigError("config SHA-256 no longer matches INIT evidence")
        source = path.parent / Path(values["data"]["path"])
        if source.is_symlink() or not source.is_file():
            raise ConfigError("configured CSV source must exist as a regular non-symlink file")
        content = source.read_bytes()
        actual_sha = _sha256(content)
        if actual_sha != values["data"]["sha256"]:
            raise ConfigError("configured CSV source SHA-256 no longer matches INIT evidence")
        _, verified_sha = _read_source(source, values["data"]["target"])
        if verified_sha != actual_sha:
            raise ConfigError("configured CSV changed while its INIT evidence was being verified")
        return LoadedConfig(values, config_sha, actual_sha)
    except ConfigError:
        raise
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot load config: {exc}") from exc
