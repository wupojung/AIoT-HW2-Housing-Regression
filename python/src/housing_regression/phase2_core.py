"""Phase 2 synthetic CSV profiling with a fixed, conservative Ames taxonomy."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import statistics
from pathlib import Path
from typing import Any, Literal

from housing_regression.contracts import phase_schema_path, validate_document
from housing_regression.core_utils import PhaseCoreError
from housing_regression.init_config import ConfigError, load_config


_FIELD_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_. -]{0,63}$")
_MISSING = {"", "na", "n/a", "nan", "null", "none"}
SYNTHETIC_MOCK = "synthetic_mock"
FORMAL_DEVELOPMENT = "formal_development"
Phase2DataMode = Literal["synthetic_mock", "formal_development"]

AMES_FIELD_TYPES = {
    **dict.fromkeys((
        "LotFrontage", "LotArea", "MasVnrArea", "BsmtFinSF1", "BsmtFinSF2", "BsmtUnfSF",
        "TotalBsmtSF", "1stFlrSF", "2ndFlrSF", "LowQualFinSF", "GrLivArea", "GarageArea",
        "WoodDeckSF", "OpenPorchSF", "EnclosedPorch", "3SsnPorch", "ScreenPorch", "PoolArea",
        "MiscVal", "YearBuilt", "YearRemodAdd", "GarageYrBlt",
    ), "continuous"),
    **dict.fromkeys((
        "BsmtFullBath", "BsmtHalfBath", "FullBath", "HalfBath", "BedroomAbvGr", "KitchenAbvGr",
        "TotRmsAbvGrd", "Fireplaces", "GarageCars", "MoSold", "YrSold",
    ), "discrete"),
    **dict.fromkeys((
        "OverallQual", "OverallCond", "ExterQual", "ExterCond", "BsmtQual", "BsmtCond",
        "BsmtExposure", "BsmtFinType1", "BsmtFinType2", "HeatingQC", "KitchenQual", "FireplaceQu",
        "GarageFinish", "GarageQual", "GarageCond", "PoolQC", "Fence", "Functional",
        "LotShape", "LandSlope",
    ), "ordinal"),
    **dict.fromkeys((
        "MSZoning", "Street", "Alley", "LotConfig", "Neighborhood", "Condition1", "Condition2",
        "BldgType", "HouseStyle", "RoofStyle", "RoofMatl", "Exterior1st", "Exterior2nd",
        "MasVnrType", "Foundation", "Heating", "CentralAir", "Electrical", "GarageType",
        "PavedDrive", "MiscFeature", "SaleType", "SaleCondition", "Utilities", "LandContour",
        "MSSubClass",
    ), "nominal"),
}


def _missing(value: str) -> bool:
    return value.strip().casefold() in _MISSING


def _format_number(value: float) -> int | float:
    rounded = round(value, 6)
    return int(rounded) if rounded.is_integer() else rounded


def _analysis(
    analysis_id: str,
    title: str,
    description: str,
    finding: str,
    image_ref: str | None = None,
    status: str = "MOCK",
    limitations: str | None = None,
) -> dict[str, Any]:
    return {
        "id": analysis_id,
        "figure_id": f"figure-{analysis_id}",
        "title": title,
        "status": status,
        "image_ref": image_ref,
        "table_ref": None,
        "description": description,
        "finding": finding,
        "limitations": limitations or (
            "MOCK from a synthetic CSV only; not an Ames research finding. "
            "Aggregate-only output; raw rows, row identifiers, and source paths are omitted."
        ),
        "provenance_ref": None,
    }


def _svg_header(title: str, description: str, width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-labelledby="chart-title chart-description" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'<title id="chart-title">{html.escape(title)}</title>\n'
        f'<desc id="chart-description">{html.escape(description)}</desc>\n'
        '<rect width="100%" height="100%" fill="#ffffff"/>\n'
        '<style>text{font-family:Arial,sans-serif;fill:#243447}.bar{fill:#3977a8}</style>\n'
    )


def _missingness_svg(
    missing_counts: dict[str, int], row_count: int, data_mode: Phase2DataMode
) -> str:
    ranked = sorted(
        missing_counts.items(),
        key=lambda item: (-(item[1] / row_count), item[0]),
    )[:20]
    width = 760
    height = 100 + 25 * len(ranked)
    if data_mode == FORMAL_DEVELOPMENT:
        description = (
            "Formal training engineering smoke: aggregate missingness for "
            f"{len(ranked)} of {len(missing_counts)} fields; no row values are shown."
        )
        title = "Formal training missingness engineering smoke"
        watermark = "FORMAL TRAINING | ENGINEERING SMOKE"
    else:
        description = (
            f"Synthetic aggregate missingness percentages for {len(ranked)} of "
            f"{len(missing_counts)} fields across {row_count} rows; no row values are shown."
        )
        title = "MOCK synthetic missingness by field"
        watermark = "MOCK | SYNTHETIC DATA"
    svg = [_svg_header(title, description, width, height)]
    svg.append('<text x="18" y="27" font-size="18" font-weight="bold">Missingness by field</text>\n')
    svg.append(f'<text x="18" y="49" font-size="12" fill="#8a3c20">{watermark}</text>\n')
    plot_x, plot_width = 220, 430
    for index, (name, count) in enumerate(ranked):
        y = 73 + 25 * index
        percent = count / row_count * 100
        bar_width = plot_width * percent / 100
        svg.append(f'<text x="18" y="{y + 14}" font-size="12">{html.escape(name)}</text>\n')
        svg.append(f'<rect class="bar" x="{plot_x}" y="{y}" width="{bar_width:.2f}" height="16"/>\n')
        svg.append(f'<text x="{plot_x + plot_width + 8}" y="{y + 13}" font-size="11">{percent:.1f}%</text>\n')
    svg.append('</svg>\n')
    return "".join(svg)


def _target_distribution_svg(
    target: str, values: list[float], data_mode: Phase2DataMode
) -> tuple[str | None, str]:
    formal = data_mode == FORMAL_DEVELOPMENT
    unavailable_prefix = "Formal training target distribution unavailable:" if formal else "Target distribution unavailable:"
    if len(values) < 2:
        return None, f"{unavailable_prefix} fewer than two non-missing numeric values."
    minimum, maximum = min(values), max(values)
    if minimum == maximum:
        return None, f"{unavailable_prefix} target values are constant."
    span = maximum - minimum
    if not math.isfinite(span):
        return None, f"{unavailable_prefix} target range is outside the safe numeric range."

    bins = min(10, max(3, math.ceil(math.sqrt(len(values)))))
    counts = [0] * bins
    for value in values:
        index = min(bins - 1, int((value - minimum) / span * bins))
        counts[index] += 1

    width, height = 760, 360
    plot_x, plot_y, plot_width, plot_height = 66, 90, 650, 205
    bar_slot = plot_width / bins
    max_count = max(counts)
    if formal:
        description = (
            f"Formal training engineering smoke histogram for {target}, grouped into {bins} bins. "
            "Bin edges and individual values are omitted; this is not the approved empirical report."
        )
        title = f"Formal training target distribution engineering smoke: {target}"
        watermark = "FORMAL TRAINING | ENGINEERING SMOKE"
        finding = (
            f"Formal training target distribution summarized in {bins} bins from "
            f"{len(values)} non-missing observations; engineering smoke only."
        )
    else:
        description = (
            f"MOCK synthetic histogram of {len(values)} non-missing numeric {target} values "
            f"grouped into {bins} bins. Bin edges and individual values are omitted."
        )
        title = f"MOCK synthetic distribution of {target}"
        watermark = "MOCK | SYNTHETIC DATA"
        finding = (
            f"Numeric target distribution summarized in {bins} bins from "
            f"{len(values)} non-missing synthetic observations; raw values omitted."
        )
    svg = [_svg_header(title, description, width, height)]
    svg.append(f'<text x="18" y="27" font-size="18" font-weight="bold">Target distribution</text>\n')
    svg.append(f'<text x="18" y="49" font-size="12" fill="#8a3c20">{watermark}</text>\n')
    svg.append(f'<text x="18" y="70" font-size="12">Target: {html.escape(target)}; bin edges omitted</text>\n')
    svg.append(f'<line x1="{plot_x}" y1="{plot_y + plot_height}" x2="{plot_x + plot_width}" y2="{plot_y + plot_height}" stroke="#536273"/>\n')
    for index, count in enumerate(counts):
        bar_height = plot_height * count / max_count if max_count else 0
        x = plot_x + index * bar_slot + 3
        y = plot_y + plot_height - bar_height
        svg.append(f'<rect class="bar" x="{x:.2f}" y="{y:.2f}" width="{max(1, bar_slot - 6):.2f}" height="{bar_height:.2f}"/>\n')
        svg.append(f'<text x="{x + bar_slot / 2 - 3:.2f}" y="{max(84, y - 5):.2f}" font-size="11">{count}</text>\n')
        svg.append(f'<text x="{x + bar_slot / 2 - 13:.2f}" y="{plot_y + plot_height + 20}" font-size="10">Bin {index + 1}</text>\n')
    svg.append(f'<text x="{plot_x}" y="{height - 18}" font-size="11">{len(values)} aggregated observations</text>\n')
    svg.append('</svg>\n')
    return "".join(svg), finding


def _emit_phase2(case_root: str | os.PathLike[str], document: dict[str, Any], assets: dict[str, str]) -> None:
    root = Path(case_root)
    if root.is_symlink() or not root.is_dir():
        raise PhaseCoreError("case_root must be an existing non-symlink directory")
    phase_dir = root / "phases" / "phase-02"
    figures_dir = phase_dir / "figures"
    for directory in (root / "phases", phase_dir, figures_dir if assets else None):
        if directory is None:
            continue
        if directory.is_symlink():
            raise PhaseCoreError("Phase 2 output path must not traverse a symbolic link")
        directory.mkdir(exist_ok=True)
        if not directory.is_dir():
            raise PhaseCoreError("Phase 2 output path component is not a directory")

    outputs = {phase_dir / "analyses.json": (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")}
    outputs.update({figures_dir / name: content.encode("utf-8") for name, content in assets.items()})
    protected_paths = set(outputs) | {
        figures_dir / "missingness.svg",
        figures_dir / "target-distribution.svg",
    }
    if any(path.exists() or path.is_symlink() for path in protected_paths):
        raise PhaseCoreError("refusing to overwrite existing Phase 2 output evidence")

    created: list[Path] = []
    try:
        for path, payload in outputs.items():
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
        raise PhaseCoreError("could not write Phase 2 output evidence") from exc


def _read_rows(
    config_path: Path, expected_sha: str, source_relative: str, target: str
) -> tuple[list[str], list[list[str]]]:
    source = config_path.parent / source_relative
    if source.is_symlink() or not source.is_file():
        raise PhaseCoreError("configured CSV is unavailable or unsafe")
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise PhaseCoreError("configured CSV cannot be read") from exc
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha:
        raise PhaseCoreError("configured synthetic CSV SHA-256 changed")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader)
    except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
        raise PhaseCoreError("CSV must have a valid UTF-8 header") from exc
    if not header or any(not column.strip() for column in header) or len(set(header)) != len(header):
        raise PhaseCoreError("CSV header must have unique non-empty columns")
    if any(not _FIELD_NAME.fullmatch(name) for name in header):
        raise PhaseCoreError("CSV has a field name outside the safe public-name pattern")
    if target not in header:
        raise PhaseCoreError("configured target is absent from the CSV")

    rows: list[list[str]] = []
    try:
        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(header):
                raise PhaseCoreError(f"CSV has an invalid column count at line {line_number}")
            rows.append(row)
    except csv.Error as exc:
        raise PhaseCoreError("CSV has malformed quoting") from exc
    return header, rows


def build_phase2(
    config_path: str | os.PathLike[str],
    case_root: str | os.PathLike[str],
    *,
    data_mode: Phase2DataMode = SYNTHETIC_MOCK,
) -> dict[str, Any]:
    """Write Phase 2 JSON/SVG under case_root using an explicit provenance mode.

    The default ``synthetic_mock`` mode preserves the G2 fixture behavior. The
    ``formal_development`` mode is reserved for explicitly authorized training
    data engineering smokes and never labels the output MOCK or synthetic.
    """
    if data_mode not in (SYNTHETIC_MOCK, FORMAL_DEVELOPMENT):
        raise PhaseCoreError("data_mode must be synthetic_mock or formal_development")
    formal = data_mode == FORMAL_DEVELOPMENT
    mode_status = "VERIFIED" if formal else "MOCK"
    limitations = (
        "FORMAL DEVELOPMENT engineering smoke only. The existing approved empirical "
        "Phase 2 report remains authoritative; this output is not a research finding "
        "or publication artifact. Raw rows, row identifiers, and source paths are omitted."
        if formal
        else None
    )
    config_file = Path(config_path)
    try:
        config = load_config(config_file)
    except ConfigError as exc:
        raise PhaseCoreError("INIT config or source evidence is invalid") from exc
    data_config = config.values["data"]
    header, rows = _read_rows(
        config_file, config.source_sha256, data_config["path"], data_config["target"]
    )
    if not rows:
        document = {
            "schema_version": "1.0.0",
            "case_id": config.values["case_id"],
            "status": "UNAVAILABLE",
            "default_analysis_id": None,
            "analyses": [],
        }
        validate_document(document, phase_schema_path(2))
        _emit_phase2(case_root, document, {})
        return document

    data_rows = {name: [] for name in header}
    for row in rows:
        for name, value in zip(header, row):
            data_rows[name].append(value)
    total_rows = len(rows)
    decisions: dict[str, tuple[str, str]] = {}
    numeric: dict[str, list[float]] = {}
    nominal_values: dict[str, set[str]] = {}
    invalid_numeric: set[str] = set()
    missing_counts = {name: sum(_missing(value) for value in data_rows[name]) for name in header}

    for name in header:
        if name == data_config["target"]:
            decisions[name] = ("target", "exclude")
        elif name.casefold() == "id":
            decisions[name] = ("identifier", "exclude")
        else:
            field_type = AMES_FIELD_TYPES.get(name, "unknown")
            if field_type == "unknown":
                decisions[name] = ("unknown", "exclude")
            else:
                decisions[name] = (field_type, "include")
                if field_type in ("continuous", "discrete"):
                    numeric[name] = []
                elif field_type == "nominal":
                    nominal_values[name] = set()

    for name, (field_type, decision) in decisions.items():
        if decision != "include":
            continue
        if field_type in ("continuous", "discrete"):
            for value in data_rows[name]:
                if _missing(value):
                    continue
                try:
                    numeric_value = float(value)
                except ValueError:
                    invalid_numeric.add(name)
                    break
                if not math.isfinite(numeric_value):
                    invalid_numeric.add(name)
                    break
                numeric[name].append(numeric_value)
        elif field_type == "nominal":
            nominal_values[name].update(value.strip() for value in data_rows[name] if not _missing(value))

    for name in invalid_numeric:
        decisions[name] = ("invalid_numeric", "exclude")

    target_values: list[float] = []
    invalid_target = False
    for value in data_rows[data_config["target"]]:
        if _missing(value):
            continue
        try:
            target_value = float(value)
        except ValueError:
            invalid_target = True
            break
        if not math.isfinite(target_value):
            invalid_target = True
            break
        target_values.append(target_value)

    missingness_ref = "phases/phase-02/figures/missingness.svg"
    target_ref = "phases/phase-02/figures/target-distribution.svg"
    missingness_svg = _missingness_svg(missing_counts, total_rows, data_mode)
    if invalid_target:
        target_svg = None
        target_finding = (
            "Formal training target distribution unavailable: target contains non-numeric values."
            if formal
            else "Target distribution unavailable: target contains non-numeric values."
        )
    else:
        target_svg, target_finding = _target_distribution_svg(
            data_config["target"], target_values, data_mode
        )
    assets = {"missingness.svg": missingness_svg}
    if target_svg is not None:
        assets["target-distribution.svg"] = target_svg

    decision_text = "; ".join(
        f"{name} [{kind}] {decision}"
        for name, (kind, decision) in decisions.items()
    ) or "No fields were present."
    missing_text = "; ".join(
        f"{name}={missing_counts[name]}/{total_rows}"
        for name in header
    ) or "No fields were present."
    numeric_summaries = []
    for name, values in numeric.items():
        if name in invalid_numeric or not values:
            continue
        numeric_summaries.append(
            f"{name}: n={len(values)}, min={_format_number(min(values))}, "
            f"median={_format_number(statistics.median(values))}, max={_format_number(max(values))}"
        )
    cardinalities = [f"{name}: {len(values)} distinct" for name, values in nominal_values.items()]
    summary_text = "; ".join(numeric_summaries + cardinalities) or "No supported included feature values."

    analyses = [
        _analysis(
            "field-decisions", "Field classification and feature decisions",
            "Fixed Ames field taxonomy; target and identifier are never features, and unknown columns are excluded.",
            decision_text,
            status=mode_status,
            limitations=limitations,
        ),
        _analysis(
            "missingness", "Aggregate missingness",
            "Counts missing cells by field without exposing row values.",
            f"Rows={total_rows}; missing cells by field: {missing_text}",
            image_ref=missingness_ref,
            status=mode_status,
            limitations=limitations,
        ),
        _analysis(
            "target-distribution",
            "Formal training target distribution" if formal else "Synthetic target distribution",
            (
                "Binned numeric target distribution for a formal training engineering smoke; "
                "the approved empirical Phase 2 report remains authoritative."
                if formal
                else "A deterministic histogram of binned synthetic target values; raw values are omitted."
            ),
            target_finding,
            image_ref=target_ref if target_svg is not None else None,
            status=mode_status if target_svg is not None else "UNAVAILABLE",
            limitations=limitations,
        ),
        _analysis(
            "feature-summary", "Safe feature aggregates",
            "Numeric range summaries and nominal cardinalities for included features only.",
            summary_text,
            status=mode_status,
            limitations=limitations,
        ),
    ]
    document = {
        "schema_version": "1.0.0",
        "case_id": config.values["case_id"],
        "status": mode_status,
        "default_analysis_id": analyses[0]["id"],
        "analyses": analyses,
    }
    validate_document(document, phase_schema_path(2))
    _emit_phase2(case_root, document, assets)
    return document
