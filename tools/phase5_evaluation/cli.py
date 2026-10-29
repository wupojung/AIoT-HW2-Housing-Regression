"""Gate-bound Phase 5 Evaluation exporter for synthetic and Phase 4 OOF inputs."""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime
import hashlib
import json
import math
import os
import statistics
import socket
import stat
import sys
import tempfile
import csv
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).with_name("evaluation-index.schema.json")
HANDOFF_SCHEMA_PATH = Path(__file__).with_name("private-oof-handoff.schema.json")
PHASE4_SCHEMA_PATH = Path(__file__).parents[1] / "research_export" / "phase-04.schema.json"
METRIC_NAMES = ("mae", "rmse", "r2")
FIGURE_IDS = ("FIG-P5-01", "FIG-P5-02", "FIG-P5-03")


class CliError(Exception):
    def __init__(self, code: str, message: str, exit_code: int = 3) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CliError("INVALID_INPUT", f"cannot read {label}: {exc}", 3) from exc
    if not isinstance(value, dict):
        raise CliError("INVALID_INPUT", f"{label} must be a JSON object", 3)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise CliError("INVALID_INPUT", f"cannot read source file: {exc}", 3) from exc
    return digest.hexdigest()


def _safe_relative(value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CliError("PATH_BLOCKED", f"{label} must be a non-empty forward-slash relative path")
    path = Path(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise CliError("PATH_BLOCKED", f"{label} must not be absolute or traverse directories")
    if ":" in value:
        raise CliError("PATH_BLOCKED", f"{label} must not contain a drive or URL scheme")
    return path


def _resolve_allowlisted_source(manifest_path: Path, manifest: dict[str, Any], gate: dict[str, Any]) -> tuple[Path, str]:
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise CliError("INVALID_INPUT", "synthetic manifest needs a source object")
    relative = _safe_relative(source.get("path"), label="source.path")
    claimed_digest = source.get("sha256")
    if not isinstance(claimed_digest, str) or len(claimed_digest) != 64:
        raise CliError("HASH_MISMATCH", "source.sha256 must be a SHA-256 hex digest")
    try:
        int(claimed_digest, 16)
    except ValueError as exc:
        raise CliError("HASH_MISMATCH", "source.sha256 must be hexadecimal") from exc

    input_root_value = gate.get("input_root")
    if not isinstance(input_root_value, str) or not input_root_value:
        raise CliError("NOT_AUTHORIZED", "gate.input_root is required")
    input_root = Path(input_root_value).expanduser().resolve(strict=True)
    if not input_root.is_dir():
        raise CliError("NOT_AUTHORIZED", "gate.input_root must be an existing directory")

    # The manifest path is relative to the manifest directory, and must resolve to
    # the exact same allowlisted relative path beneath the approved input root.
    manifest_root = manifest_path.parent.resolve(strict=True)
    if manifest_root != input_root:
        raise CliError("NOT_AUTHORIZED", "manifest must reside directly under gate.input_root")
    candidate = manifest_root / relative
    cursor = manifest_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise CliError("PATH_BLOCKED", "source path may not traverse symlinks")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(input_root)
    except ValueError as exc:
        raise CliError("PATH_BLOCKED", "source path escapes gate.input_root") from exc
    if not resolved.is_file():
        raise CliError("INVALID_INPUT", "source path must be a regular file")

    allowlist = gate.get("input_allowlist")
    if not isinstance(allowlist, list):
        raise CliError("NOT_AUTHORIZED", "gate.input_allowlist must be a list")
    matching = [
        item for item in allowlist
        if isinstance(item, dict) and item.get("path") == relative.as_posix()
    ]
    if len(matching) != 1:
        raise CliError("NOT_AUTHORIZED", "source must appear exactly once in gate.input_allowlist")
    allowed_digest = matching[0].get("sha256")
    actual_digest = _sha256(resolved)
    if allowed_digest != claimed_digest or actual_digest != claimed_digest:
        raise CliError("HASH_MISMATCH", "source digest does not match manifest, gate, and file")
    if manifest.get("mode") != "synthetic" or source.get("kind") != "synthetic_prediction_pairs":
        raise CliError("NOT_AUTHORIZED", "only explicitly marked synthetic prediction pairs are accepted")
    return resolved, actual_digest


def _build_handoff_evaluations(index_case_id: str, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[tuple[float, float]]]]:
    target = data["target"]
    if not isinstance(target, dict) or not isinstance(target.get("column"), str) or not isinstance(target.get("unit"), str):
        raise CliError("NOT_AUTHORIZED", "gate.target must define target column and unit")
    evaluations = []
    plot_data = {}
    for config_id, group in sorted(data["groups"].items()):
        folds = group["folds"]
        per_fold = {fold: _metric_values(pairs) for fold, pairs in sorted(folds.items())}
        fold_mean = {name: (sum(m[name] for m in per_fold.values()) / len(per_fold)
                            if all(m[name] is not None for m in per_fold.values()) else None) for name in METRIC_NAMES}
        sample_sd = {name: (statistics.stdev([m[name] for m in per_fold.values()])
                            if all(m[name] is not None for m in per_fold.values()) and len(per_fold) > 1 else None)
                     for name in METRIC_NAMES}
        fold_id, pooled_id = f"{config_id}-fold-mean", f"{config_id}-pooled-oof"
        prediction_origin = ("fold_specific_all_features_ols" if group["track"] == "baseline"
                             else "fold_specific_selected_to_ols")
        base_manifest = {"execution_run_id": data["run_id"], "configuration_id": config_id,
                         "prediction_origin": prediction_origin, "protocol_version": data["protocol"], "target": target}
        fold_eval = _base_evaluation(fold_id, base_manifest, len(group["rows"]), fold_mean,
                                     data["csv_digest"], "cv_fold_mean",
                                     {"fold_count": len(folds), "aggregation": "fold_mean", "ddof": 1,
                                      "sample_sd": sample_sd, "fold_values_ref": None}, [pooled_id])
        pooled_eval = _base_evaluation(pooled_id, base_manifest, len(group["rows"]),
                                       _metric_values(group["rows"]), data["csv_digest"], "pooled_oof", None, [fold_id])
        for evaluation in (fold_eval, pooled_eval):
            evaluation["metrics"] = {name: {"value": value, "status": "VERIFIED" if value is not None else "UNAVAILABLE",
                                             "reason_code": None if value is not None else "METRIC_UNDEFINED",
                                             "evidence_ref": f"sha256:{data['csv_digest']}"}
                                      for name, value in (fold_mean.items() if evaluation is fold_eval else _metric_values(group["rows"]).items())}
            evaluation["evidence"]["source_ref"] = (
                f"Phase 4 manifest sha256:{data.get('manifest_digest', 'not-recorded-in-unit-fixture')}; "
                f"summary sha256:{data['summary_digest']}"
            )
            evaluation["interval"]["int_f"]["reason_code"] = "NO_INTERVAL_METHOD_REVIEW"
            evaluation["interval"]["int_s"]["reason_code"] = "NO_INTERVAL_EVIDENCE"
            evaluation["limitations"] = ["Development OOF only; not independent generalization; no final fit or Holdout evidence."]
            evaluation["review_status"] = "AWAITING_REVIEW"
        histogram_ref = f"assets/{pooled_id}-FIG-P5-03-histogram.json"
        pooled_eval["figures"] = [{
            "figure_id": fig_id, "evaluation_id": pooled_id, "configuration_id": config_id,
            "evaluation_population": "development_oof", "prediction_origin": prediction_origin,
            "n": len(group["rows"]), "status": "PLANNED", "publication_review": "PENDING",
            "asset_ref": f"assets/{pooled_id}-{fig_id.lower()}.png", "sha256": None,
            "accessible_table_ref": None, "alt": None, "finding": None,
            "limitations": ["Development OOF diagnostic; publication review pending."], "source_digest": data["csv_digest"],
            "axes": _real_axes(fig_id, target["unit"]),
            "residual_sign": "actual_minus_predicted" if fig_id != "FIG-P5-01" else None,
            "histogram": {"bin_count": 30, "bin_edges_ref": histogram_ref, "n": len(group["rows"])} if fig_id == "FIG-P5-03" else None,
        } for fig_id in ("FIG-P5-02", "FIG-P5-01", "FIG-P5-03")]
        pooled_eval["asset_status"] = "AVAILABLE"
        evaluations.extend((fold_eval, pooled_eval))
        plot_data[pooled_id] = group["rows"]
    default_id = next((item["evaluation_id"] for item in evaluations if item["metric_source"] == "cv_fold_mean"), None)
    return ({"schema_version": "1.0.0", "case_id": index_case_id, "release_id": None,
             "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
             "status": "PLANNED", "reason_code": "PUBLICATION_REVIEW_PENDING", "publication_review": "PENDING",
             "default_evaluation_id": default_id, "evaluations": evaluations,
             "ui": _build_empty({"case_id": index_case_id})["ui"]}, plot_data)


def _real_axes(figure_id: str, unit: str) -> dict[str, Any]:
    return {
        "FIG-P5-01": {"x": {"field": "actual", "label": "Actual", "unit": unit}, "y": {"field": "predicted", "label": "Predicted", "unit": unit}, "reference_line": "y_equals_x"},
        "FIG-P5-02": {"x": {"field": "predicted", "label": "Predicted", "unit": unit}, "y": {"field": "actual_minus_predicted", "label": "Actual - Predicted", "unit": unit}, "reference_line": "y_equals_0"},
        "FIG-P5-03": {"x": {"field": "actual_minus_predicted", "label": "Residual", "unit": unit}, "y": {"field": "count", "label": "Count", "unit": "count"}, "reference_line": "x_equals_0"},
    }[figure_id]


def _histogram(values: list[float], bin_count: int = 30) -> tuple[list[float], list[int]]:
    if not values or any(not math.isfinite(value) for value in values):
        raise CliError("INVALID_INPUT", "histogram requires finite pooled residuals")
    low, high = min(values), max(values)
    if low == high:
        low, high = low - 0.5, high + 0.5
    width = (high - low) / bin_count
    edges = [low + index * width for index in range(bin_count)] + [high]
    counts = [0] * bin_count
    for value in values:
        index = max(0, min(bisect.bisect_right(edges, value) - 1, bin_count - 1))
        counts[index] += 1
    return edges, counts


def _write_real_figures(output_root: Path, index: dict[str, Any], plot_data: dict[str, list[tuple[float, float]]]) -> list[dict[str, Any]]:
    """Render all pooled diagnostics off-tree, then promote the set with rollback."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise CliError("DEPENDENCY_MISSING", "install the tool-local matplotlib requirement", 5) from exc

    assets_dir = output_root / "assets"
    if assets_dir.is_symlink():
        raise CliError("PATH_BLOCKED", "asset output directory may not be a symlink")
    assets_dir.mkdir(exist_ok=True)
    if not assets_dir.is_dir():
        raise CliError("PATH_BLOCKED", "asset output path must be a directory")

    staged_to_final: list[tuple[Path, Path]] = []
    staged_figure_digests: list[tuple[dict[str, Any], str]] = []
    with tempfile.TemporaryDirectory(prefix=".phase5-asset-stage-", dir=output_root) as stage_name:
        stage_assets = Path(stage_name) / "assets"
        stage_assets.mkdir()
        try:
            for evaluation in index["evaluations"]:
                if evaluation["metric_source"] != "pooled_oof":
                    continue
                pairs = plot_data[evaluation["evaluation_id"]]
                actual = [pair[0] for pair in pairs]
                predicted = [pair[1] for pair in pairs]
                residual = [y - yhat for y, yhat in pairs]
                for figure in evaluation["figures"]:
                    asset_ref = figure.get("asset_ref")
                    parts = Path(asset_ref).parts if isinstance(asset_ref, str) else ()
                    if len(parts) != 2 or parts[0] != "assets":
                        raise CliError("PATH_BLOCKED", "figure asset_ref must be a case-root assets path")
                    filename = parts[1]
                    staged_png = stage_assets / filename
                    final_png = assets_dir / filename
                    if final_png.exists() or final_png.is_symlink():
                        raise CliError("OUTPUT_EXISTS", f"refusing to overwrite figure asset: {final_png}", 5)

                    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
                    histogram_evidence = None
                    try:
                        if figure["figure_id"] == "FIG-P5-01":
                            ax.scatter(actual, predicted, s=12, alpha=.7)
                            low, high = min(actual + predicted), max(actual + predicted)
                            ax.plot([low, high], [low, high], color="black", linewidth=1)
                            ax.set(xlabel="Actual", ylabel="Predicted")
                        elif figure["figure_id"] == "FIG-P5-02":
                            ax.scatter(predicted, residual, s=12, alpha=.7)
                            ax.axhline(0, color="black", linewidth=1)
                            ax.set(xlabel="Predicted", ylabel="Actual - Predicted")
                        else:
                            histogram_evidence = _histogram(residual, figure["histogram"]["bin_count"])
                            ax.hist(residual, bins=histogram_evidence[0])
                            ax.axvline(0, color="black", linewidth=1)
                            ax.set(xlabel="Actual - Predicted", ylabel="Count")
                        fig.savefig(staged_png, format="png", dpi=120)
                    except Exception as exc:
                        raise CliError("OUTPUT_WRITE_FAILED", f"figure rendering failed: {exc}", 5) from exc
                    finally:
                        plt.close(fig)
                    staged_figure_digests.append((figure, _sha256(staged_png)))
                    staged_to_final.append((staged_png, final_png))

                    if figure["figure_id"] == "FIG-P5-03":
                        histogram = figure["histogram"]
                        edges, counts = histogram_evidence
                        histogram_name = Path(histogram["bin_edges_ref"]).name
                        staged_histogram = stage_assets / histogram_name
                        final_histogram = assets_dir / histogram_name
                        if final_histogram.exists() or final_histogram.is_symlink():
                            raise CliError("OUTPUT_EXISTS", f"refusing to overwrite histogram data: {final_histogram}", 5)
                        payload = {"bin_edges": edges, "counts": counts, "n": len(residual),
                                   "residual_sign": "actual_minus_predicted"}
                        staged_histogram.write_text(json.dumps(payload, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")
                        if sum(counts) != histogram["n"]:
                            raise CliError("INVALID_INPUT", "histogram bin counts do not sum to pooled OOF n")
                        staged_to_final.append((staged_histogram, final_histogram))

            for _, destination in staged_to_final:
                if destination.exists() or destination.is_symlink():
                    raise CliError("OUTPUT_EXISTS", f"refusing to overwrite asset: {destination}", 5)
            receipts: list[dict[str, Any]] = []
            rollback_errors: list[str] = []
            try:
                for staged, destination in staged_to_final:
                    staged_info = staged.lstat()
                    expected_digest = _sha256(staged)
                    os.link(staged, destination)
                    info = destination.lstat()
                    if (not stat.S_ISREG(info.st_mode)
                            or (info.st_dev, info.st_ino) != (staged_info.st_dev, staged_info.st_ino)
                            or _sha256(destination) != expected_digest):
                        rollback_errors.append(f"ownership/integrity could not be verified; kept {destination.name}")
                        raise OSError("promoted asset ownership/integrity verification failed")
                    receipts.append({"path": destination, "device": info.st_dev, "inode": info.st_ino,
                                     "sha256": expected_digest})
                for figure, digest in staged_figure_digests:
                    figure["sha256"] = digest
                return receipts
            except Exception as exc:
                rollback_errors.extend(_rollback_real_assets(receipts))
                suffix = f"; rollback errors: {'; '.join(rollback_errors)}" if rollback_errors else ""
                if isinstance(exc, FileExistsError):
                    raise CliError("OUTPUT_EXISTS", f"asset promotion collided: {exc}{suffix}", 5) from exc
                raise CliError("OUTPUT_WRITE_FAILED", f"asset-set promotion failed: {exc}{suffix}", 5) from exc
        except CliError:
            raise
        except OSError as exc:
            raise CliError("OUTPUT_WRITE_FAILED", f"asset staging failed: {exc}", 5) from exc


def _rollback_real_assets(receipts: list[dict[str, Any]]) -> list[str]:
    """Remove only files whose inode and bytes still match this export's receipt."""
    problems = []
    for receipt in reversed(receipts):
        path = receipt["path"]
        try:
            before = path.lstat()
            if (not stat.S_ISREG(before.st_mode) or before.st_dev != receipt["device"]
                    or before.st_ino != receipt["inode"]):
                problems.append(f"kept changed asset {path.name}")
                continue
            digest = _sha256(path)
            after = path.lstat()
            if ((after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
                    or digest != receipt["sha256"]):
                problems.append(f"kept modified asset {path.name}")
                continue
            path.unlink()
        except FileNotFoundError:
            continue
        except (OSError, CliError) as exc:
            problems.append(f"could not remove owned asset {path.name}: {exc}")
    return problems


def _finalize_phase4_output(index: dict[str, Any], plot_data: dict[str, list[tuple[float, float]]],
                            output_root: Path) -> Path:
    receipts = _write_real_figures(output_root, index, plot_data)
    try:
        return _write_index(index, output_root)
    except Exception as exc:
        rollback_problems = _rollback_real_assets(receipts)
        index_path = output_root / "phases" / "phase-05" / "evaluations.json"
        if index_path.exists() or index_path.is_symlink():
            rollback_problems.append("index destination exists after failed atomic write; preserved")
        if rollback_problems:
            raise CliError("OUTPUT_WRITE_FAILED", f"index write failed; asset rollback incomplete: {'; '.join(rollback_problems)}", 5) from exc
        raise


def _validate_gate(manifest_path: Path, manifest: dict[str, Any], gate: dict[str, Any],
                   output_root_arg: str, operation: str) -> Path:
    if gate.get("authorized") is not True or gate.get("mode") != "synthetic_only":
        raise CliError("NOT_AUTHORIZED", "gate must explicitly authorize synthetic_only processing")
    if not isinstance(gate.get("gate_id"), str) or not gate["gate_id"]:
        raise CliError("NOT_AUTHORIZED", "gate.gate_id is required")
    operations = gate.get("allowed_operations")
    if not isinstance(operations, list) or operation not in operations:
        raise CliError("NOT_AUTHORIZED", f"gate does not allow operation {operation!r}")

    host = gate.get("host")
    if not isinstance(host, dict):
        raise CliError("NOT_AUTHORIZED", "gate.host is required")
    input_root_value = gate.get("input_root")
    if not isinstance(input_root_value, str) or not input_root_value:
        raise CliError("NOT_AUTHORIZED", "gate.input_root is required")
    input_root = Path(input_root_value).expanduser().resolve(strict=True)
    if not input_root.is_dir():
        raise CliError("NOT_AUTHORIZED", "gate.input_root must be an existing directory")
    manifest_root = manifest_path.parent.resolve(strict=True)
    if manifest_root != input_root:
        raise CliError("NOT_AUTHORIZED", "manifest must reside directly under gate.input_root")

    actual_platform = {"darwin": "macos", "win32": "windows"}.get(sys.platform, sys.platform)
    if host.get("platform") != actual_platform:
        raise CliError("HOST_MISMATCH", "gate host platform does not match this runtime")
    if host.get("host_id") != socket.gethostname():
        raise CliError("HOST_MISMATCH", "gate host identity does not match this runtime")
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if host.get("python_version") != actual_python:
        raise CliError("HOST_MISMATCH", "gate Python version does not match this runtime")
    if host.get("python_executable") != str(Path(sys.executable).resolve()):
        raise CliError("HOST_MISMATCH", "gate Python executable does not match this runtime")

    output_root = Path(output_root_arg).expanduser().resolve(strict=True)
    allowed_root_value = gate.get("output_root")
    if not isinstance(allowed_root_value, str) or not allowed_root_value:
        raise CliError("NOT_AUTHORIZED", "gate.output_root is required")
    allowed_root = Path(allowed_root_value).expanduser().resolve(strict=True)
    if not output_root.is_dir() or output_root != allowed_root:
        raise CliError("PATH_BLOCKED", "--output-root must exactly match the existing gate.output_root directory")
    if manifest.get("manifest_version") != 1:
        raise CliError("INVALID_INPUT", "manifest_version must be 1")
    if manifest.get("case_id") is None:
        raise CliError("INVALID_INPUT", "manifest.case_id is required")
    return output_root


def _metric_values(pairs: list[tuple[float, float]]) -> dict[str, float | None]:
    if not pairs:
        raise CliError("INVALID_INPUT", "at least one prediction pair is required")
    actual = [pair[0] for pair in pairs]
    predicted = [pair[1] for pair in pairs]
    if any(not math.isfinite(value) for value in actual + predicted):
        raise CliError("INVALID_INPUT", "actual and predicted values must be finite")
    residuals = [y - yhat for y, yhat in pairs]
    try:
        mae = sum(abs(value) for value in residuals) / len(residuals)
        rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals))
        mean_y = sum(actual) / len(actual)
        total = sum((value - mean_y) ** 2 for value in actual)
        r2 = None if total == 0 else 1.0 - sum(value * value for value in residuals) / total
    except OverflowError as exc:
        raise CliError("INVALID_INPUT", "synthetic metric calculation overflowed") from exc
    if not math.isfinite(mae) or not math.isfinite(rmse):
        raise CliError("INVALID_INPUT", "synthetic metric calculation is non-finite")
    if r2 is not None and not math.isfinite(r2):
        r2 = None
    return {"mae": mae, "rmse": rmse, "r2": r2}


def _mock_metric(value: float | None, digest: str, name: str) -> dict[str, Any]:
    if value is None or not math.isfinite(value):
        return {
            "value": None,
            "status": "UNAVAILABLE",
            "reason_code": "SYNTHETIC_METRIC_UNDEFINED",
            "evidence_ref": None,
        }
    return {
        "value": value,
        "status": "MOCK",
        "reason_code": "SYNTHETIC_ONLY_NOT_EMPIRICAL",
        "evidence_ref": f"synthetic-fixture:{digest}:{name}",
    }


def _figure_slots(evaluation_id: str, configuration_id: str, n: int,
                  prediction_origin: str, unit: str, digest: str) -> list[dict[str, Any]]:
    common = {
        "evaluation_id": evaluation_id,
        "configuration_id": configuration_id,
        "evaluation_population": "development_oof",
        "prediction_origin": prediction_origin,
        "n": n,
        "status": "UNAVAILABLE",
        "publication_review": "PENDING",
        "asset_ref": None,
        "sha256": None,
        "accessible_table_ref": None,
        "alt": None,
        "finding": None,
        "limitations": ["SYNTHETIC METADATA ONLY; NO FIGURE ASSET OR EMPIRICAL DATA"],
        "source_digest": digest,
    }
    axes = {
        "FIG-P5-01": {
            "x": {"field": "actual", "label": "Actual", "unit": unit},
            "y": {"field": "predicted", "label": "Predicted", "unit": unit},
            "reference_line": "y_equals_x",
        },
        "FIG-P5-02": {
            "x": {"field": "predicted", "label": "Predicted", "unit": unit},
            "y": {"field": "actual_minus_predicted", "label": "Actual - Predicted", "unit": unit},
            "reference_line": "y_equals_0",
        },
        "FIG-P5-03": {
            "x": {"field": "actual_minus_predicted", "label": "Residual", "unit": unit},
            "y": {"field": "count", "label": "Count", "unit": "count"},
            "reference_line": "x_equals_0",
        },
    }
    figures = []
    for figure_id in FIGURE_IDS:
        item = dict(common)
        item.update({
            "figure_id": figure_id,
            "axes": axes[figure_id],
            "residual_sign": "actual_minus_predicted" if figure_id != "FIG-P5-01" else None,
            "histogram": {
                "bin_count": 5,
                "bin_edges_ref": f"synthetic-only-fixed-bins:{digest}",
                "n": n,
            } if figure_id == "FIG-P5-03" else None,
        })
        figures.append(item)
    return figures


def _base_evaluation(evaluation_id: str, manifest: dict[str, Any], n: int,
                     metrics: dict[str, float | None], digest: str,
                     metric_source: str, fold_summary: dict[str, Any] | None,
                     linked: list[str]) -> dict[str, Any]:
    target = manifest["target"]
    return {
        "evaluation_id": evaluation_id,
        "execution_run_id": manifest["execution_run_id"],
        "configuration_id": manifest["configuration_id"],
        "final_fit_id": None,
        "model_id": None,
        "model_version": None,
        "evaluation_population": "development_oof",
        "prediction_origin": manifest["prediction_origin"],
        "metric_source": metric_source,
        "n": n,
        "target": {"column": target["column"], "unit": target["unit"]},
        "metrics": {name: _mock_metric(metrics[name], digest, name) for name in METRIC_NAMES},
        "fold_summary": fold_summary,
        "figures": [],
        "interval": {
            "int_f": {
                "status": "UNAVAILABLE",
                "reason_code": "SYNTHETIC_ONLY_NO_METHOD_REVIEW",
                "method": None,
                "assumptions_ref": None,
            },
            "int_s": {
                "status": "UNAVAILABLE",
                "reason_code": "SYNTHETIC_ONLY_NO_INTERVAL_EVIDENCE",
                "interval_type": None,
                "method": None,
                "nominal_level": None,
                "population": None,
                "asset_ref": None,
                "coverage_evidence": None,
                "review_url": None,
            },
        },
        "evidence": {
            "source_artifact_sha256": digest,
            "source_ref": "synthetic-input-only",
            "protocol_version": manifest["protocol_version"],
            "review_url": None,
        },
        "asset_status": "UNAVAILABLE",
        "review_status": "AWAITING_REVIEW",
        "limitations": ["SYNTHETIC MOCK ONLY; NOT A REAL EVALUATION"],
        "linked_evaluation_ids": linked,
    }


def _build_empty(manifest: dict[str, Any]) -> dict[str, Any]:
    case_id = manifest.get("case_id")
    if not isinstance(case_id, str):
        raise CliError("INVALID_INPUT", "empty manifest case_id must be a string")
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "release_id": None,
        "generated_at": None,
        "status": "UNAVAILABLE",
        "reason_code": manifest.get("reason_code") or "NO_APPROVED_EVALUATIONS",
        "publication_review": "PENDING",
        "default_evaluation_id": None,
        "evaluations": [],
        "ui": {
            "default_population": "development_oof",
            "population_options": [
                {"id": "development_oof", "label": "Development OOF"},
                {"id": "holdout", "label": "Holdout aggregate"},
            ],
            "figure_tabs": [
                {"figure_id": "FIG-P5-02", "label": "Residual vs Predicted", "kind": "residual_vs_predicted"},
                {"figure_id": "FIG-P5-01", "label": "Actual vs Predicted", "kind": "actual_vs_predicted"},
                {"figure_id": "FIG-P5-03", "label": "Residual Distribution", "kind": "residual_distribution"},
            ],
            "metric_order": list(METRIC_NAMES),
            "interval_figure_id": "FIG-P5-04",
        },
    }


def _build_synthetic(manifest: dict[str, Any], rows: list[dict[str, Any]], digest: str) -> dict[str, Any]:
    for key in ("execution_run_id", "configuration_id", "prediction_origin", "protocol_version"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise CliError("INVALID_INPUT", f"synthetic manifest {key} is required")
    target = manifest.get("target")
    if not isinstance(target, dict) or not isinstance(target.get("column"), str) or not isinstance(target.get("unit"), str):
        raise CliError("INVALID_INPUT", "target.column and target.unit are required strings")
    if not rows:
        raise CliError("INVALID_INPUT", "synthetic predictions must contain rows")

    folds: dict[str, list[tuple[float, float]]] = {}
    all_pairs: list[tuple[float, float]] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("fold_id"), str):
            raise CliError("INVALID_INPUT", "each synthetic row needs a string fold_id")
        actual, predicted = row.get("actual"), row.get("predicted")
        if isinstance(actual, bool) or isinstance(predicted, bool) or not isinstance(actual, (int, float)) or not isinstance(predicted, (int, float)):
            raise CliError("INVALID_INPUT", "synthetic actual and predicted values must be numbers")
        pair = (float(actual), float(predicted))
        if not math.isfinite(pair[0]) or not math.isfinite(pair[1]):
            raise CliError("INVALID_INPUT", "synthetic actual and predicted values must be finite")
        folds.setdefault(row["fold_id"], []).append(pair)
        all_pairs.append(pair)
    if len(folds) < 2 or any(len(values) < 2 for values in folds.values()):
        raise CliError("INVALID_INPUT", "at least two folds with at least two rows each are required")

    per_fold = {fold_id: _metric_values(pairs) for fold_id, pairs in sorted(folds.items())}
    fold_mean = {
        name: (
            sum(values[name] for values in per_fold.values()) / len(per_fold)
            if all(values[name] is not None for values in per_fold.values())
            else None
        )
        for name in METRIC_NAMES
    }
    sample_sd = {}
    for name in METRIC_NAMES:
        values = [metrics[name] for metrics in per_fold.values()]
        sample_sd[name] = (
            statistics.stdev(values)
            if len(values) >= 2 and all(value is not None for value in values)
            else None
        )

    fold_id, pooled_id = "synthetic-fold-mean", "synthetic-pooled-oof"
    fold_eval = _base_evaluation(
        fold_id, manifest, len(all_pairs), fold_mean, digest, "cv_fold_mean",
        {
            "fold_count": len(folds),
            "aggregation": "fold_mean",
            "ddof": 1,
            "sample_sd": sample_sd,
            "fold_values_ref": None,
        },
        [pooled_id],
    )
    pooled_eval = _base_evaluation(
        pooled_id, manifest, len(all_pairs), _metric_values(all_pairs), digest,
        "pooled_oof", None, [fold_id],
    )
    pooled_eval["figures"] = _figure_slots(
        pooled_id, manifest["configuration_id"], len(all_pairs),
        manifest["prediction_origin"], target["unit"], digest,
    )
    return {
        "schema_version": "1.0.0",
        "case_id": manifest["case_id"],
        "release_id": None,
        "generated_at": None,
        "status": "MOCK",
        "reason_code": "SYNTHETIC_FIXTURE_ONLY",
        "publication_review": "PENDING",
        "default_evaluation_id": fold_id,
        "evaluations": [fold_eval, pooled_eval],
        "ui": _build_empty({"case_id": manifest["case_id"]})["ui"],
    }


def _validate_identity(index: dict[str, Any]) -> None:
    evaluations = index.get("evaluations")
    if not isinstance(evaluations, list):
        raise CliError("JOIN_BLOCKED", "evaluations must be a list", 4)
    ids = [item.get("evaluation_id") for item in evaluations if isinstance(item, dict)]
    if (len(ids) != len(evaluations)
            or any(not isinstance(value, str) for value in ids)
            or len(set(ids)) != len(ids)):
        raise CliError("JOIN_BLOCKED", "evaluation IDs must be present and unique", 4)
    by_id = {item["evaluation_id"]: item for item in evaluations}
    default_id = index.get("default_evaluation_id")
    if default_id is not None and (not isinstance(default_id, str) or default_id not in by_id):
        raise CliError("JOIN_BLOCKED", "default_evaluation_id must refer to an evaluation", 4)
    for item in evaluations:
        links = item.get("linked_evaluation_ids")
        if (not isinstance(links, list)
                or any(not isinstance(link, str) for link in links)
                or len(links) != len(set(links))):
            raise CliError("JOIN_BLOCKED", "linked_evaluation_ids must be a unique list", 4)
        for linked_id in links:
            other = by_id.get(linked_id)
            if other is None or item["evaluation_id"] not in other.get("linked_evaluation_ids", []):
                raise CliError("JOIN_BLOCKED", "evaluation links must exist and be reciprocal", 4)
            for key in ("execution_run_id", "configuration_id", "evaluation_population", "prediction_origin"):
                if item.get(key) != other.get(key):
                    raise CliError("JOIN_BLOCKED", f"linked evaluations disagree on {key}", 4)
            evidence = item.get("evidence")
            other_evidence = other.get("evidence")
            if not isinstance(evidence, dict) or not isinstance(other_evidence, dict):
                raise CliError("JOIN_BLOCKED", "linked evaluations need evidence objects", 4)
            for key in ("source_artifact_sha256", "protocol_version"):
                if evidence.get(key) != other_evidence.get(key):
                    raise CliError("JOIN_BLOCKED", f"linked evaluations disagree on evidence.{key}", 4)
            if item.get("metric_source") == other.get("metric_source"):
                raise CliError("JOIN_BLOCKED", "linked evaluations must have distinct metric_source values", 4)
        figures = item.get("figures")
        if not isinstance(figures, list):
            raise CliError("JOIN_BLOCKED", "figures must be a list", 4)
        figure_ids = []
        for figure in figures:
            if not isinstance(figure, dict):
                raise CliError("JOIN_BLOCKED", "each figure must be an object", 4)
            figure_ids.append(figure.get("figure_id"))
            for key in ("evaluation_id", "configuration_id", "evaluation_population", "prediction_origin", "n"):
                expected = item.get(key)
                if figure.get(key) != expected:
                    raise CliError("JOIN_BLOCKED", f"figure identity disagrees on {key}", 4)
        if any(not isinstance(value, str) for value in figure_ids) or len(set(figure_ids)) != len(figure_ids):
            raise CliError("JOIN_BLOCKED", "figure IDs must be unique strings within an evaluation", 4)


def _schema_validate(index: dict[str, Any]) -> None:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise CliError("DEPENDENCY_MISSING", "install tools/phase5_evaluation/requirements.txt in the authorized isolated environment", 5) from exc
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(index),
            key=lambda error: list(map(str, error.absolute_path)),
        )
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        raise CliError("SCHEMA_FAIL", f"cannot validate pinned schema: {exc}", 4) from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise CliError("SCHEMA_FAIL", f"{location}: {first.message}", 4)


def _atomic_write_new(path: Path, data: bytes) -> None:
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".phase5-", suffix=".tmp", delete=False
        ) as stream:
            temporary_name = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # A same-directory hard link provides atomic creation with no replacement.
        # It fails if another process already created the destination.
        os.link(temporary_name, path)
    except FileExistsError as exc:
        raise CliError("OUTPUT_EXISTS", f"refusing to overwrite existing output: {path}", 5) from exc
    except OSError as exc:
        raise CliError("OUTPUT_WRITE_FAILED", f"atomic output creation failed: {exc}", 5) from exc
    finally:
        if temporary_name is not None:
            try:
                temporary_name.unlink(missing_ok=True)
            except OSError:
                pass


def _write_index(index: dict[str, Any], output_root: Path) -> Path:
    phase_dir = output_root / "phases" / "phase-05"
    output_file = phase_dir / "evaluations.json"
    if output_file.exists() or output_file.is_symlink():
        raise CliError("OUTPUT_EXISTS", f"refusing to overwrite existing output: {output_file}", 5)
    # Do not follow a pre-existing symlink in any output component.
    cursor = output_root
    for name in ("phases", "phase-05"):
        cursor = cursor / name
        if cursor.is_symlink():
            raise CliError("PATH_BLOCKED", f"output path contains a symlink: {cursor}")
        cursor.mkdir(exist_ok=True)
        if not cursor.is_dir():
            raise CliError("PATH_BLOCKED", f"output component is not a directory: {cursor}")
    try:
        output_file.resolve(strict=False).relative_to(output_root)
    except ValueError as exc:
        raise CliError("PATH_BLOCKED", "output path escapes gate.output_root") from exc
    payload = (json.dumps(index, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    _atomic_write_new(output_file, payload)
    return output_file


def _export(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).expanduser().resolve(strict=True)
    gate_path = Path(args.gate).expanduser().resolve(strict=True)
    manifest = _load_json(manifest_path, label="manifest")
    gate = _load_json(gate_path, label="gate")
    output_root = _validate_gate(manifest_path, manifest, gate, args.output_root, "export")

    mode = manifest.get("mode")
    if mode == "empty":
        if manifest.get("source") is not None:
            raise CliError("INVALID_INPUT", "empty manifest must not declare a source")
        index = _build_empty(manifest)
    elif mode == "synthetic":
        source_path, digest = _resolve_allowlisted_source(manifest_path, manifest, gate)
        source = _load_json(source_path, label="synthetic source")
        if source.get("fixture_kind") != "synthetic":
            raise CliError("NOT_AUTHORIZED", "source file is not marked fixture_kind=synthetic")
        rows = source.get("rows")
        if not isinstance(rows, list):
            raise CliError("INVALID_INPUT", "synthetic source rows must be a list")
        index = _build_synthetic(manifest, rows, digest)
    else:
        raise CliError("NOT_AUTHORIZED", "synthetic Phase 5 export accepts only empty or synthetic manifests")

    _validate_identity(index)
    _schema_validate(index)
    output = _write_index(index, output_root)
    print(f"EXPORTED {output}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    index_path = Path(args.index).expanduser().resolve(strict=True)
    index = _load_json(index_path, label="evaluation index")
    _validate_identity(index)
    _schema_validate(index)
    print(f"VALID {index_path}")
    return 0


def _evaluate_handoff(args: argparse.Namespace) -> int:
    """Evaluate only the normalized private handoff, never Phase 4 source files."""
    handoff_root = Path(args.handoff_root).expanduser().resolve(strict=True)
    package_root = Path(args.package_root).expanduser().resolve(strict=True)
    gate = _load_json(Path(args.gate).expanduser().resolve(strict=True), label="Phase 5 handoff gate")
    if gate.get("authorized") is not True or gate.get("mode") != "phase5_handoff_evaluation":
        raise CliError("NOT_AUTHORIZED", "gate must authorize phase5_handoff_evaluation")
    if "evaluate_handoff" not in gate.get("allowed_operations", []):
        raise CliError("NOT_AUTHORIZED", "gate does not allow evaluate_handoff")
    if not isinstance(gate.get("gate_id"), str) or not gate["gate_id"]:
        raise CliError("NOT_AUTHORIZED", "gate.gate_id is required")
    input_root = Path(gate.get("input_root", "")).expanduser().resolve(strict=True)
    output_root = Path(gate.get("output_root", "")).expanduser().resolve(strict=True)
    if handoff_root != input_root or package_root != output_root:
        raise CliError("PATH_BLOCKED", "handoff/package roots must exactly match gate input_root/output_root")
    if handoff_root == package_root or handoff_root.is_relative_to(package_root) or package_root.is_relative_to(handoff_root):
        raise CliError("PATH_BLOCKED", "private handoff and Case Package roots must be separate, non-nested directories")
    host = gate.get("host")
    actual_platform = {"darwin": "macos", "win32": "windows"}.get(sys.platform, sys.platform)
    if (not isinstance(host, dict) or host.get("platform") != actual_platform
            or host.get("host_id") != socket.gethostname()
            or host.get("python_version") != f"{sys.version_info.major}.{sys.version_info.minor}"
            or host.get("python_executable") != str(Path(sys.executable).resolve())):
        raise CliError("HOST_MISMATCH", "gate host does not match this runtime")

    package_path = package_root / "package.json"
    if package_path.is_symlink() or not package_path.is_file():
        raise CliError("PATH_BLOCKED", "package.json must be a regular non-symlink file")
    package = _load_json(package_path, label="Case Package manifest")
    package_files = package.get("files")
    if not isinstance(package_files, list):
        raise CliError("JOIN_BLOCKED", "package.files must be a list", 4)
    file_records: dict[str, dict[str, Any]] = {}
    for record in package_files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str) or record["path"] in file_records:
            raise CliError("JOIN_BLOCKED", "package.files paths must be unique", 4)
        rel = _safe_relative(record["path"], label="package.files.path")
        path = package_root / rel
        cursor = package_root
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise CliError("PATH_BLOCKED", f"package path contains a symlink: {record['path']}")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(package_root)
        except (OSError, ValueError) as exc:
            raise CliError("PATH_BLOCKED", f"package file escapes or is missing: {record['path']}", 4) from exc
        if not resolved.is_file():
            raise CliError("HASH_MISMATCH", f"package file missing or unsafe: {record['path']}", 4)
        payload = resolved.read_bytes()
        if hashlib.sha256(payload).hexdigest() != record.get("sha256") or len(payload) != record.get("bytes"):
            raise CliError("HASH_MISMATCH", f"package file digest mismatch: {record['path']}", 4)
        file_records[record["path"]] = record
    case_id = package.get("case_id")
    modeling_rel = "phases/phase-04/modeling.json"
    if modeling_rel not in file_records:
        raise CliError("JOIN_BLOCKED", "package does not declare its Phase 4 modeling file", 4)
    modeling = _load_json(package_root / modeling_rel, label="Phase 4 modeling")
    _schema_validate_phase4(modeling)
    eval_rel = "phases/phase-05/evaluations.json"
    if eval_rel not in file_records:
        raise CliError("JOIN_BLOCKED", "package does not declare its Phase 5 evaluation slot", 4)
    current_index_path = package_root / eval_rel
    current_index = _load_json(current_index_path, label="empty Phase 5 slot")
    if (current_index.get("case_id") != case_id or current_index.get("evaluations") != []
            or current_index.get("status") != "UNAVAILABLE"):
        raise CliError("NOT_AUTHORIZED", "Phase 5 package slot is not the expected unavailable empty slot")

    handoff_path = handoff_root / "handoff.json"
    csv_path = handoff_root / "oof.csv"
    if any(path.is_symlink() or not path.is_file() for path in (handoff_path, csv_path)):
        raise CliError("PATH_BLOCKED", "handoff.json and oof.csv must be regular non-symlink files")
    handoff = _load_json(handoff_path, label="private OOF handoff")
    _schema_validate_handoff(handoff)
    allowlist = gate.get("input_allowlist")
    expected_allowlist = [{"path": "handoff.json", "sha256": _sha256(handoff_path)},
                          {"path": "oof.csv", "sha256": _sha256(csv_path)}]
    if allowlist != expected_allowlist:
        raise CliError("NOT_AUTHORIZED", "gate input_allowlist must bind exactly handoff.json and oof.csv")
    if gate.get("handoff_sha256") != expected_allowlist[0]["sha256"]:
        raise CliError("HASH_MISMATCH", "gate handoff_sha256 does not match handoff.json")
    if handoff.get("csv", {}).get("sha256") != expected_allowlist[1]["sha256"]:
        raise CliError("HASH_MISMATCH", "handoff CSV digest does not match oof.csv")
    if (handoff.get("case_id") != case_id or gate.get("case_id") != case_id
            or gate.get("execution_run_id") != handoff.get("execution_run_id")
            or gate.get("protocol_id") != handoff.get("protocol_id")
            or gate.get("protocol_version") != handoff.get("protocol_version")
            or handoff.get("population") != "development_oof"):
        raise CliError("JOIN_BLOCKED", "gate, handoff, and package case/run/protocol identities disagree", 4)
    runs = modeling.get("execution_runs", [])
    matching_runs = [run for run in runs if isinstance(run, dict)
                     and run.get("execution_run_id") == handoff.get("execution_run_id")]
    if (modeling.get("case_id") != case_id or modeling.get("cv", {}).get("protocol_id") != handoff.get("protocol_id")
            or len(matching_runs) != 1
            or matching_runs[0].get("source_manifest_sha256") != handoff.get("source_artifacts", {}).get("manifest_sha256")):
        raise CliError("JOIN_BLOCKED", "handoff identity does not join to Phase 4 modeling", 4)
    configs = {item.get("configuration_id"): item for item in modeling.get("configurations", []) if isinstance(item, dict)}
    selected = handoff.get("configurations")
    if not isinstance(selected, list) or not selected:
        raise CliError("JOIN_BLOCKED", "handoff configurations must be non-empty", 4)
    for config in selected:
        model_config = configs.get(config.get("configuration_id"))
        if (model_config is None or model_config.get("status") != "VERIFIED"
                or model_config.get("configuration_id") != "cfg-" + config.get("config_hash", "")
                or model_config.get("method_id") != config.get("method_id")
                or model_config.get("track_id") != config.get("track_id")):
            raise CliError("JOIN_BLOCKED", "handoff configuration does not join to verified Phase 4 configuration", 4)
    if gate.get("manifest_sha256") != handoff.get("source_artifacts", {}).get("manifest_sha256"):
        raise CliError("HASH_MISMATCH", "gate manifest_sha256 differs from handoff provenance")

    expected_columns = ["row_id", "configuration_id", "fold_index", "task_id", "actual", "predicted"]
    groups: dict[str, dict[str, Any]] = {
        item["configuration_id"]: {"folds": {}, "rows": [], "track": item["track_id"]}
        for item in selected
    }
    task_map = {}
    for item in selected:
        for task in item["fold_tasks"]:
            key = (item["configuration_id"], task["fold_index"])
            if key in task_map:
                raise CliError("JOIN_BLOCKED", "handoff has duplicate configuration/fold tasks", 4)
            task_map[key] = task["task_id"]
    seen_rows: set[tuple[str, str]] = set()
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != expected_columns:
                raise CliError("JOIN_BLOCKED", "handoff CSV columns do not match the normalized contract", 4)
            count = 0
            for row in reader:
                if None in row or any(row.get(name) is None for name in expected_columns):
                    raise CliError("JOIN_BLOCKED", "handoff CSV row has missing or extra fields", 4)
                config_id = row["configuration_id"]
                try:
                    fold = int(row["fold_index"])
                    actual, predicted = float(row["actual"]), float(row["predicted"])
                except (TypeError, ValueError) as exc:
                    raise CliError("INVALID_INPUT", "handoff fold and prediction values must be numeric") from exc
                row_identity = (config_id, row["row_id"])
                if (config_id not in groups or not row["row_id"] or row_identity in seen_rows
                        or task_map.get((config_id, fold)) != row["task_id"]
                        or not math.isfinite(actual) or not math.isfinite(predicted)):
                    raise CliError("JOIN_BLOCKED", "handoff row identity, task join, or values are invalid", 4)
                seen_rows.add(row_identity)
                group = groups[config_id]
                group["rows"].append((actual, predicted))
                group["folds"].setdefault(str(fold), []).append((actual, predicted))
                count += 1
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CliError("INVALID_INPUT", f"cannot read normalized handoff CSV: {exc}") from exc
    if count != handoff.get("row_count") or any(len(group["rows"]) != handoff.get("n_per_configuration") for group in groups.values()):
        raise CliError("JOIN_BLOCKED", "handoff row counts do not match its contract", 4)
    expected_folds = [str(fold) for fold in handoff.get("expected_fold_ids", [])]
    for group in groups.values():
        if sorted(group["folds"]) != sorted(expected_folds) or any(not rows for rows in group["folds"].values()):
            raise CliError("JOIN_BLOCKED", "handoff fold coverage is incomplete", 4)
    data = {"target": handoff["target"], "groups": groups, "run_id": handoff["execution_run_id"],
            "protocol": handoff["protocol_version"], "csv_digest": handoff["csv"]["sha256"],
            "manifest_digest": handoff["source_artifacts"]["manifest_sha256"],
            "summary_digest": handoff["source_artifacts"]["summary_sha256"]}
    index, plot_data = _build_handoff_evaluations(case_id, data)
    for evaluation in index["evaluations"]:
        for figure in evaluation["figures"]:
            figure["alt"] = _figure_alt(figure["figure_id"])
    _validate_identity(index)
    _schema_validate(index)
    receipts = _write_real_figures(package_root, index, plot_data)
    try:
        figure_manifest_path = package_root / "assets" / "figure-manifest.json"
        figure_manifest = _build_figure_manifest(case_id, index, package_root)
        figure_manifest_payload = (json.dumps(figure_manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        _atomic_write_new(figure_manifest_path, figure_manifest_payload)
        info = figure_manifest_path.lstat()
        receipts.append({"path": figure_manifest_path, "device": info.st_dev, "inode": info.st_ino,
                         "sha256": hashlib.sha256(figure_manifest_payload).hexdigest()})

        index_payload = (json.dumps(index, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        new_manifest = dict(package)
        new_manifest["asset_manifest_ref"] = "assets/figure-manifest.json"
        phases = dict(new_manifest.get("phases", {}))
        phase5 = dict(phases.get("phase5", {}))
        phase5["status"] = index["status"]
        phases["phase5"] = phase5
        new_manifest["phases"] = phases
        new_files = [dict(record) for record in package_files]
        replacement = {"path": eval_rel, "sha256": hashlib.sha256(index_payload).hexdigest(),
                       "bytes": len(index_payload), "mime": "application/json"}
        new_files = [replacement if record["path"] == eval_rel else record for record in new_files]
        for receipt in receipts:
            rel = receipt["path"].relative_to(package_root).as_posix()
            mime = "image/png" if rel.endswith(".png") else "application/json"
            new_files.append({"path": rel, "sha256": receipt["sha256"], "bytes": receipt["path"].stat().st_size,
                              "mime": mime})
        new_manifest["files"] = sorted(new_files, key=lambda record: record["path"])
        if len({record["path"] for record in new_files}) != len(new_files):
            raise CliError("JOIN_BLOCKED", "package.files contains a duplicate path", 4)
        _validate_figure_manifest(case_id, index, figure_manifest, package_root,
                                  {record["path"]: record for record in new_files},
                                  figure_manifest_payload, index_payload)
        manifest_payload = (json.dumps(new_manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        original_index = current_index_path.read_bytes()
        original_package = package_path.read_bytes()
        _atomic_replace_existing(current_index_path, index_payload)
        _atomic_replace_existing(package_path, manifest_payload)
    except Exception as exc:
        restore_errors = []
        try:
            if "original_package" in locals() and package_path.read_bytes() != original_package:
                _atomic_replace_existing(package_path, original_package)
        except Exception as restore_exc:
            restore_errors.append(f"package restore failed: {restore_exc}")
        try:
            if "original_index" in locals() and current_index_path.read_bytes() != original_index:
                _atomic_replace_existing(current_index_path, original_index)
        except Exception as restore_exc:
            restore_errors.append(f"index restore failed: {restore_exc}")
        rollback = _rollback_real_assets(receipts)
        if rollback or restore_errors:
            details = "; ".join(restore_errors + [f"asset rollback: {rollback}"] if rollback else restore_errors)
            raise CliError("OUTPUT_WRITE_FAILED", f"package update failed; rollback incomplete: {details}", 5) from exc
        raise
    print(f"EVALUATED {current_index_path}")
    return 0


def _figure_alt(figure_id: str) -> str:
    return {
        "FIG-P5-01": "Development OOF actual versus predicted values; review pending.",
        "FIG-P5-02": "Development OOF residuals versus predicted values; review pending.",
        "FIG-P5-03": "Development OOF residual distribution; review pending.",
    }.get(figure_id, "Development OOF diagnostic; review pending.")


def _build_figure_manifest(case_id: str, index: dict[str, Any], package_root: Path) -> dict[str, Any]:
    figures = []
    for evaluation in index["evaluations"]:
        for figure in evaluation["figures"]:
            png_ref = figure.get("asset_ref")
            if not isinstance(png_ref, str):
                raise CliError("JOIN_BLOCKED", "generated Phase 5 figure needs a package asset_ref", 4)
            png_path = package_root / _safe_relative(png_ref, label="figure.asset_ref")
            payload = png_path.read_bytes()
            if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
                raise CliError("OUTPUT_WRITE_FAILED", "generated figure is not a valid PNG", 5)
            width = int.from_bytes(payload[16:20], "big")
            height = int.from_bytes(payload[20:24], "big")
            figures.append({
                "figure_id": figure["figure_id"], "case_id": case_id, "phase": "phase5",
                "source_configuration_id": figure["configuration_id"],
                "source_evaluation_id": figure["evaluation_id"], "svg_ref": None, "png_ref": png_ref,
                "width": width, "height": height, "alt": figure["alt"], "accessible_table_ref": None,
                "source_evidence_ref": f"sha256:{figure['source_digest']}", "sha256_svg": None,
                "sha256_png": hashlib.sha256(payload).hexdigest(), "publication_review": "PENDING",
                "status": "PLANNED",
            })
    return {"schema_version": "1.0.0", "case_id": case_id,
            "status": "PLANNED" if figures else "UNAVAILABLE", "figures": figures}


def _validate_figure_manifest(case_id: str, index: dict[str, Any], figure_manifest: dict[str, Any],
                              package_root: Path, package_files: dict[str, dict[str, Any]],
                              figure_manifest_payload: bytes, index_payload: bytes) -> None:
    package_root = package_root.resolve(strict=True)
    if figure_manifest.get("case_id") != case_id or figure_manifest.get("schema_version") != "1.0.0":
        raise CliError("JOIN_BLOCKED", "figure manifest case/schema identity mismatch", 4)
    entries = figure_manifest.get("figures")
    if not isinstance(entries, list):
        raise CliError("JOIN_BLOCKED", "figure manifest figures must be a list", 4)
    try:
        if json.loads(figure_manifest_payload.decode("utf-8")) != figure_manifest:
            raise CliError("HASH_MISMATCH", "figure manifest payload differs from validated contents", 4)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CliError("INVALID_INPUT", "figure manifest payload is not UTF-8 JSON", 4) from exc
    manifest_path = package_root / "assets/figure-manifest.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or manifest_path.read_bytes() != figure_manifest_payload):
        raise CliError("HASH_MISMATCH", "physical figure manifest differs from its validated payload", 4)

    evaluations: dict[str, dict[str, Any]] = {}
    expected: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for evaluation in index.get("evaluations", []):
        evaluation_id = evaluation.get("evaluation_id")
        if not isinstance(evaluation_id, str) or evaluation_id in evaluations:
            raise CliError("JOIN_BLOCKED", "evaluation IDs must be unique for figure joins", 4)
        evaluations[evaluation_id] = evaluation
        for figure in evaluation.get("figures", []):
            key = (evaluation_id, figure.get("figure_id"))
            if key in expected:
                raise CliError("JOIN_BLOCKED", "duplicate figure token within one Evaluation", 4)
            expected[key] = (evaluation, figure)

    seen_keys: set[tuple[str, str, str]] = set()
    seen_assets: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise CliError("JOIN_BLOCKED", "figure manifest entries must be objects", 4)
        evaluation_id = entry.get("source_evaluation_id")
        figure_id = entry.get("figure_id")
        phase = entry.get("phase")
        if (not isinstance(phase, str) or not isinstance(evaluation_id, str)
                or not isinstance(figure_id, str)):
            raise CliError("JOIN_BLOCKED", "figure manifest composite identity fields must be strings", 4)
        key = (phase, evaluation_id, figure_id)
        if key in seen_keys:
            raise CliError("JOIN_BLOCKED", "duplicate (phase, source_evaluation_id, figure_id) figure key", 4)
        seen_keys.add(key)
        pair = expected.get((evaluation_id, figure_id))
        if phase != "phase5" or pair is None or entry.get("case_id") != case_id:
            raise CliError("JOIN_BLOCKED", "figure manifest entry does not join to a Phase 5 Evaluation", 4)
        evaluation, figure = pair
        if entry.get("source_configuration_id") != evaluation.get("configuration_id"):
            raise CliError("JOIN_BLOCKED", "figure manifest configuration does not match its owning Evaluation", 4)
        asset_ref = entry.get("png_ref")
        if not isinstance(asset_ref, str):
            raise CliError("JOIN_BLOCKED", "figure manifest PNG ref must be a string", 4)
        if asset_ref in seen_assets:
            raise CliError("JOIN_BLOCKED", "each Evaluation figure needs its own physical PNG path", 4)
        if asset_ref != figure.get("asset_ref"):
            raise CliError("JOIN_BLOCKED", "figure manifest PNG refs must be unique and match the owning Evaluation", 4)
        seen_assets.add(asset_ref)
        rel = _safe_relative(asset_ref, label="figure manifest png_ref")
        path = package_root / rel
        cursor = package_root
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise CliError("PATH_BLOCKED", "figure manifest PNG path contains a symlink")
        try:
            path.resolve(strict=True).relative_to(package_root)
        except (OSError, ValueError) as exc:
            raise CliError("PATH_BLOCKED", "figure manifest PNG path escapes the Case Package", 4) from exc
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        record = package_files.get(asset_ref)
        if (record is None or record.get("mime") != "image/png" or record.get("sha256") != digest
                or record.get("bytes") != len(payload) or entry.get("sha256_png") != digest
                or figure.get("sha256") != digest):
            raise CliError("HASH_MISMATCH", "figure manifest, package.files, Phase 5 index and PNG digest disagree", 4)
    if seen_keys != {("phase5", evaluation_id, figure_id) for evaluation_id, figure_id in expected}:
        raise CliError("JOIN_BLOCKED", "figure manifest must contain exactly one entry for every Evaluation figure", 4)

    manifest_record = package_files.get("assets/figure-manifest.json")
    if (manifest_record is None or manifest_record.get("sha256") != hashlib.sha256(figure_manifest_payload).hexdigest()
            or manifest_record.get("bytes") != len(figure_manifest_payload)
            or manifest_record.get("mime") != "application/json"):
        raise CliError("HASH_MISMATCH", "figure manifest is absent or mismatched in package.files", 4)
    index_record = package_files.get("phases/phase-05/evaluations.json")
    if (index_record is None or index_record.get("sha256") != hashlib.sha256(index_payload).hexdigest()
            or index_record.get("bytes") != len(index_payload)):
        raise CliError("HASH_MISMATCH", "Phase 5 index is absent or mismatched in package.files", 4)


def _schema_validate_phase4(modeling: dict[str, Any]) -> None:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
        schema = json.loads(PHASE4_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema).iter_errors(modeling))
    except ImportError as exc:
        raise CliError("DEPENDENCY_MISSING", "install tools/phase5_evaluation/requirements.txt", 5) from exc
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        raise CliError("SCHEMA_FAIL", f"cannot load pinned Phase 4 schema: {exc}", 4) from exc
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise CliError("SCHEMA_FAIL", f"Phase 4 modeling {location}: {first.message}", 4)


def _schema_validate_handoff(handoff: dict[str, Any]) -> None:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads(HANDOFF_SCHEMA_PATH.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(handoff))
    except ImportError as exc:
        raise CliError("DEPENDENCY_MISSING", "install tools/phase5_evaluation/requirements.txt", 5) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError("SCHEMA_FAIL", f"cannot load private handoff schema: {exc}", 4) from exc
    if errors:
        raise CliError("SCHEMA_FAIL", f"private handoff schema: {errors[0].message}", 4)


def _atomic_replace_existing(path: Path, payload: bytes) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".phase5-update-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise CliError("OUTPUT_WRITE_FAILED", f"atomic package update failed: {exc}", 5) from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 5 evaluation CLI for synthetic fixtures or normalized private OOF handoffs.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export", help="export an authorized empty or synthetic index")
    export_parser.add_argument("--manifest", required=True, help="explicit UTF-8 JSON input manifest")
    export_parser.add_argument("--gate", required=True, help="explicit UTF-8 JSON authorization record")
    export_parser.add_argument("--output-root", required=True, help="existing private staging root allowed by the gate")
    export_parser.set_defaults(handler=_export)
    validate_parser = subparsers.add_parser("validate", help="validate a Phase 5 index against the pinned schema")
    validate_parser.add_argument("--index", required=True, help="evaluation-index JSON to validate")
    validate_parser.set_defaults(handler=_validate)
    handoff_parser = subparsers.add_parser("evaluate-handoff", help="evaluate a normalized Phase 4 private OOF handoff in a Case Package")
    handoff_parser.add_argument("--handoff-root", required=True)
    handoff_parser.add_argument("--package-root", required=True)
    handoff_parser.add_argument("--gate", required=True)
    handoff_parser.set_defaults(handler=_evaluate_handoff)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except CliError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, ValueError) as exc:
        print(f"INVALID_INPUT: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
