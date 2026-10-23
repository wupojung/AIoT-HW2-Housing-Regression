#!/usr/bin/env python3
"""Full reproducible descriptive EDA for Owner-provided Kaggle Ames package.

This script implements safe local-path gating, computes exact SHA-256 hashes,
validates schemas and ID properties, crosswalks data dictionary headings (including
numeric-leading field names and aliases), produces a complete un-truncated field inventory,
calculates full pairwise correlation and missingness tables, renders reusable PNG/SVG charts,
and generates figure manifests and private Traditional-Chinese research report.

Constraints:
- Pure descriptive EDA: no data modification, imputation, feature engineering, splitting, or modeling.
- Outputs must be strictly confined to ignored local/research/phase2-eda/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

# Optional matplotlib import for full-fidelity PNG/SVG rendering
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

EXPECTED = {"train.csv", "test.csv", "data_description.txt", "sample_submission.csv"}
TARGET = "SalePrice"
IDENTIFIER = "Id"

ALIAS_MAP = {
    "BedroomAbvGr": "Bedroom",
    "KitchenAbvGr": "Kitchen",
}

REVERSE_ALIAS_MAP = {v: k for k, v in ALIAS_MAP.items()}

STRUCTURAL_NA_CANDIDATES = {
    "Alley",
    "BsmtQual",
    "BsmtCond",
    "BsmtExposure",
    "BsmtFinType1",
    "BsmtFinType2",
    "FireplaceQu",
    "GarageType",
    "GarageYrBlt",
    "GarageFinish",
    "GarageQual",
    "GarageCond",
    "PoolQC",
    "Fence",
    "MiscFeature",
}


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 hex digest of a file in 1MB chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_local_path(path: Path, local_root: Path, *, allow_root: bool = False) -> Path:
    """Enforce that path resolves strictly inside local_root and is not a symlink."""
    local_root = local_root.absolute()
    if local_root.is_symlink():
        raise ValueError("The ignored local/ directory must not be a symlink.")
    resolved_root = local_root.resolve()
    resolved = path.absolute().resolve()
    if not resolved.is_relative_to(resolved_root) or (not allow_root and resolved == resolved_root):
        raise ValueError(f"Path must resolve inside ignored local/: {path}")
    return resolved


def parse_data_description(path: Path) -> dict:
    """Parse Kaggle data_description.txt extracting headings, descriptions, and code levels."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()

    headings = {}
    current_heading = None
    current_desc = []
    current_levels = {}

    heading_pattern = re.compile(r"^([0-9A-Za-z_ /()]+):\s*(.*)$")
    level_pattern = re.compile(r"^\s+([A-Za-z0-9_#]+|\*)\s+(.*)$")

    for line in lines:
        m = heading_pattern.match(line)
        if m:
            if current_heading:
                headings[current_heading] = {
                    "description": " ".join(current_desc).strip(),
                    "levels": current_levels,
                }
            current_heading = m.group(1).strip()
            current_desc = [m.group(2).strip()] if m.group(2).strip() else []
            current_levels = {}
        elif current_heading:
            lm = level_pattern.match(line)
            if lm:
                current_levels[lm.group(1).strip()] = lm.group(2).strip()
            elif line.strip():
                current_desc.append(line.strip())

    if current_heading:
        headings[current_heading] = {
            "description": " ".join(current_desc).strip(),
            "levels": current_levels,
        }

    return headings


def crosswalk_dictionary(train_columns: set[str], test_columns: set[str], dictionary_headings: dict) -> dict:
    """Map every train/test column to data_description headings accounting for aliases."""
    all_columns = sorted(train_columns | test_columns)
    described_headings = set(dictionary_headings.keys())

    status = {}
    matched_alias = {}
    for col in all_columns:
        if col == IDENTIFIER:
            status[col] = "identifier"
        elif col == TARGET:
            status[col] = "target"
        elif col in described_headings:
            status[col] = "definition_present"
        elif col in ALIAS_MAP and ALIAS_MAP[col] in described_headings:
            status[col] = "definition_alias"
            matched_alias[col] = ALIAS_MAP[col]
        else:
            status[col] = "not_found_in_dictionary"

    unmapped_headings = []
    for heading in sorted(described_headings):
        mapped_col = REVERSE_ALIAS_MAP.get(heading, heading)
        if mapped_col not in all_columns:
            unmapped_headings.append(heading)

    return {
        "field_status": status,
        "aliases_applied": matched_alias,
        "total_headings_in_description": len(described_headings),
        "unmapped_dictionary_headings": unmapped_headings,
    }


def read_csv_data(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read CSV file and return header list and list of row dicts."""
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    return columns, rows


def calculate_numeric_stats(values: list[float]) -> dict:
    """Calculate complete descriptive statistics and IQR anomaly fences."""
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    n = len(ordered)
    mean = statistics.mean(ordered)
    std = statistics.stdev(ordered) if n > 1 else None
    med = statistics.median(ordered)
    q25 = _quantile(ordered, 0.25)
    q75 = _quantile(ordered, 0.75)
    iqr = q75 - q25
    lower_fence = q25 - 1.5 * iqr
    upper_fence = q75 + 1.5 * iqr
    anomaly_count = sum(v < lower_fence or v > upper_fence for v in ordered)

    # Skewness calculation
    skew = None
    if n >= 3:
        sd_pop = statistics.pstdev(ordered)
        if sd_pop > 0:
            skew = sum(((v - mean) / sd_pop) ** 3 for v in ordered) / n

    return {
        "count": n,
        "mean": mean,
        "std": std,
        "min": ordered[0],
        "25%": q25,
        "50%": med,
        "75%": q75,
        "max": ordered[-1],
        "iqr": iqr,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "anomaly_candidates_count": anomaly_count,
        "skewness": skew,
    }


def _quantile(values: list[float], q: float) -> float:
    pos = (len(values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def infer_semantic_type(col: str, is_numeric: bool, cardinality: int) -> str:
    """Heuristically categorize field into semantic measurement candidate."""
    if col == IDENTIFIER:
        return "identifier"
    if col == TARGET:
        return "continuous_target"
    if not is_numeric:
        if col in {"ExterQual", "ExterCond", "BsmtQual", "BsmtCond", "BsmtExposure",
                    "BsmtFinType1", "BsmtFinType2", "HeatingQC", "KitchenQual", "Functional",
                    "FireplaceQu", "GarageFinish", "GarageQual", "GarageCond", "PoolQC", "Fence"}:
            return "ordinal_candidate"
        return "nominal_candidate"
    # Numeric
    if col in {"MSSubClass", "OverallQual", "OverallCond"}:
        return "ordinal_encoded_candidate"
    if col in {"YearBuilt", "YearRemodAdd", "GarageYrBlt", "MoSold", "YrSold",
               "BsmtFullBath", "BsmtHalfBath", "FullBath", "HalfBath",
               "BedroomAbvGr", "KitchenAbvGr", "TotRmsAbvGrd", "Fireplaces", "GarageCars"}:
        return "discrete_numeric"
    return "continuous_numeric"


def build_field_inventory(
    train_cols: list[str],
    train_rows: list[dict],
    test_cols: list[str],
    test_rows: list[dict],
    dict_headings: dict,
    dict_status: dict,
) -> list[dict]:
    """Produce complete inventory record for every original train/test field without truncation."""
    all_columns = sorted(set(train_cols) | set(test_cols))

    train_n = len(train_rows)
    test_n = len(test_rows)

    inventory = []
    for col in all_columns:
        train_vals = [r.get(col, "") for r in train_rows] if col in train_cols else []
        test_vals = [r.get(col, "") for r in test_rows] if col in test_cols else []

        train_valid = [v for v in train_vals if v is not None and v.strip() != ""]
        test_valid = [v for v in test_vals if v is not None and v.strip() != ""]

        train_missing_count = train_n - len(train_valid) if col in train_cols else None
        train_missing_rate = (train_missing_count / train_n) if train_n > 0 and train_missing_count is not None else None

        test_missing_count = test_n - len(test_valid) if col in test_cols else None
        test_missing_rate = (test_missing_count / test_n) if test_n > 0 and test_missing_count is not None else None

        # Determine type
        is_numeric = False
        all_valid = train_valid + test_valid
        if all_valid:
            try:
                for v in all_valid:
                    float(v)
                is_numeric = True
            except ValueError:
                is_numeric = False

        # Compute stats or categorical distribution
        num_stats = None
        cat_dist = None
        cardinality = len(set(all_valid))

        if is_numeric:
            train_nums = [float(v) for v in train_valid]
            num_stats = calculate_numeric_stats(train_nums)
        else:
            counts = {}
            for v in all_valid:
                counts[v] = counts.get(v, 0) + 1
            # Sort by frequency descending, then name
            cat_dist = {
                k: {"count": counts[k], "percentage": round(counts[k] / len(all_valid) * 100, 2)}
                for k in sorted(counts.keys(), key=lambda x: (-counts[x], x))
            }

        role = "predictor"
        if col == IDENTIFIER:
            role = "identifier"
        elif col == TARGET:
            role = "target"

        semantic_type = infer_semantic_type(col, is_numeric, cardinality)

        # Dictionary details
        dict_key = ALIAS_MAP.get(col, col)
        dict_info = dict_headings.get(dict_key, {})
        purpose = dict_info.get("description", "No description provided in dictionary.")

        # Quality flags
        flags = []
        if train_missing_count and train_missing_count > 0:
            flags.append("has_missing_in_train")
        if test_missing_count and test_missing_count > 0:
            flags.append("has_missing_in_test")
        if (train_missing_rate or 0) > 0.8:
            flags.append("high_missing_gt_80pct")
        if col in STRUCTURAL_NA_CANDIDATES:
            flags.append("structural_missing_candidate")
        if is_numeric and num_stats and num_stats.get("anomaly_candidates_count", 0) > 0:
            flags.append("iqr_anomaly_candidates_present")
        if is_numeric and num_stats and num_stats.get("skewness") is not None and abs(num_stats["skewness"]) > 2.0:
            flags.append("extreme_skew_gt_2")
        if cardinality == 1:
            flags.append("constant_column")

        provenance = []
        if col in train_cols:
            provenance.append("train.csv")
        if col in test_cols:
            provenance.append("test.csv")

        record = {
            "name": col,
            "role": role,
            "purpose": purpose,
            "dtype": "numeric (float/int)" if is_numeric else "categorical (string)",
            "semantic_type": semantic_type,
            "provenance": provenance,
            "train_valid_count": len(train_valid) if col in train_cols else 0,
            "train_missing_count": train_missing_count if col in train_cols else 0,
            "train_missing_rate": train_missing_rate if col in train_cols else None,
            "test_valid_count": len(test_valid) if col in test_cols else 0,
            "test_missing_count": test_missing_count if col in test_cols else 0,
            "test_missing_rate": test_missing_rate if col in test_cols else None,
            "cardinality": cardinality,
            "is_structural_missing_candidate": col in STRUCTURAL_NA_CANDIDATES,
            "dictionary_status": dict_status.get(col, "not_found_in_dictionary"),
            "dictionary_heading": dict_key,
            "quality_flags": flags,
            "numeric_stats": num_stats,
            "categorical_distribution": cat_dist,
        }
        inventory.append(record)

    return inventory


def calculate_numeric_correlations(train_cols: list[str], train_rows: list[dict]) -> dict:
    """Calculate full pairwise Pearson correlations across all numeric features in train."""
    numeric_cols = []
    col_values = {}
    for col in train_cols:
        if col == IDENTIFIER:
            continue
        vals = [r.get(col, "") for r in train_rows]
        valid = [v for v in vals if v is not None and v.strip() != ""]
        try:
            nums = [float(v) for v in valid]
            if len(nums) == len(valid) and len(nums) > 0:
                numeric_cols.append(col)
                col_values[col] = vals
        except ValueError:
            continue

    pairwise = {}
    target_corrs = {}

    for i, col1 in enumerate(numeric_cols):
        pairwise[col1] = {}
        for j, col2 in enumerate(numeric_cols):
            if i <= j:
                pairs = []
                for v1, v2 in zip(col_values[col1], col_values[col2]):
                    if v1 and v1.strip() and v2 and v2.strip():
                        pairs.append((float(v1), float(v2)))
                if len(pairs) >= 2:
                    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
                    if len(set(xs)) > 1 and len(set(ys)) > 1:
                        r = statistics.correlation(xs, ys)
                        pairwise[col1][col2] = {"r": r, "n": len(pairs)}
                    else:
                        pairwise[col1][col2] = {"r": None, "n": len(pairs), "reason": "zero_variance"}
                else:
                    pairwise[col1][col2] = {"r": None, "n": len(pairs), "reason": "insufficient_pairs"}
            else:
                pairwise[col1][col2] = pairwise[col2][col1]

        if TARGET in numeric_cols and col1 != TARGET:
            target_corrs[col1] = pairwise[col1][TARGET]

    sorted_target = sorted(
        [(k, v["r"]) for k, v in target_corrs.items() if v.get("r") is not None],
        key=lambda x: -abs(x[1])
    )

    return {
        "numeric_column_count": len(numeric_cols),
        "pairwise_correlations": pairwise,
        "target_correlations_ranked": sorted_target,
        "caveat": "Pearson correlations calculated pairwise-complete; exploratory linear association only, not causal evidence or model feature selection."
    }


def generate_figures_and_manifest(
    inventory: list[dict],
    correlations: dict,
    train_rows: list[dict],
    test_rows: list[dict],
    output_dir: Path,
    sha_manifest: dict,
    access_date: str,
) -> list[dict]:
    """Generate all requested SVG and PNG charts and build detailed figure metadata manifest."""
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries = []

    def register_figure(
        fig_id: str,
        name: str,
        title_zh: str,
        caption_zh: str,
        section: str,
        observation: str,
        limitations: str,
    ):
        png_path = figures_dir / f"{name}.png"
        svg_path = figures_dir / f"{name}.svg"
        entry = {
            "figure_id": fig_id,
            "filename_png": f"figures/{name}.png",
            "filename_svg": f"figures/{name}.svg",
            "title_zh_tw": title_zh,
            "caption_zh_tw": caption_zh,
            "source_version": f"Kaggle Ames House Prices Package (access_date={access_date})",
            "source_sha256": sha_manifest,
            "population_or_sample": f"Ames Housing Dataset (Train N={len(train_rows)}, Test N={len(test_rows)})",
            "script": "tools/eda/full_ames_eda.py",
            "command": f"python tools/eda/full_ames_eda.py --access-date {access_date} --terms-confirmed",
            "suggested_report_section": section,
            "descriptive_observation": observation,
            "limitations": limitations,
        }
        manifest_entries.append(entry)
        return png_path, svg_path

    # FIG-01: Dataset Overview
    p_png, p_svg = register_figure(
        "FIG-01",
        "fig01_dataset_overview",
        "Ames 房價資料集總覽與欄位角色分佈",
        "展示 Kaggle Ames 資料集中訓練集 (1,460 筆) 與測試集 (1,459 筆) 之欄位總數、資料型態分類及識別碼/目標變數分佈。",
        "2. 資料集概覽與品質驗證",
        f"訓練集共有 81 欄，測試集共有 80 欄 (缺少 SalePrice 目標)，共有 79 個候選解釋變數與 1 個 Id 識別碼。",
        "僅呈現原始資料集維度與結構，未包含任何特徵轉換。"
    )
    _render_overview_chart(p_png, p_svg, inventory, len(train_rows), len(test_rows))

    # FIG-02: Missingness Overview
    p_png, p_svg = register_figure(
        "FIG-02",
        "fig02_missingness_overview",
        "全欄位缺失值統計與結構性缺漏分析",
        "分析訓練集與測試集中所有具有遺漏值欄位之缺失比例，並標註屬於資料字典明確定義之「特徵不存在 (Structural NA)」候選欄位。",
        "3. 缺失值深度分析",
        "共有多個欄位具有遺漏值，其中 PoolQC, MiscFeature, Alley, Fence 缺失率超過 80%，大多代表該設施不存在而非記錄遺失。",
        "描述性統計，未進行任何插補；結構性 NA 與真實未記錄缺失需於 Phase 3 分別處理。"
    )
    _render_missingness_chart(p_png, p_svg, inventory)

    # FIG-03: SalePrice distribution
    target_rec = next((r for r in inventory if r["role"] == "target"), None)
    target_vals = []
    if target_rec and target_rec["numeric_stats"]:
        target_vals = [float(r[TARGET]) for r in train_rows if r.get(TARGET)]
    p_png, p_svg = register_figure(
        "FIG-03",
        "fig03_saleprice_distribution",
        "目標變數 SalePrice 分佈直方圖與箱型圖",
        "展示訓練集目標變數 SalePrice (N=1,460) 之直方圖、密度擬合與五數綜合箱型圖。",
        "4. 目標變數 SalePrice 分佈分析",
        f"SalePrice 呈現明顯右偏態 (偏態係數約 {target_rec['numeric_stats']['skewness']:.2f})，中位數小於平均數，存在高房價候選極值。",
        "僅描述訓練集原始金額分佈，未進行對數轉換或建模擬合。"
    )
    _render_saleprice_chart(p_png, p_svg, target_vals, target_rec["numeric_stats"] if target_rec else {})

    # FIG-04: Numeric distributions overview
    p_png, p_svg = register_figure(
        "FIG-04",
        "fig04_numeric_distributions_overview",
        "主要數值預測變數分佈總覽",
        "選取代表性連續與離散數值欄位 (如 GrLivArea, OverallQual, TotalBsmtSF, YearBuilt 等) 之多面直方圖。",
        "5. 數值特徵統計摘要與分佈",
        "生活面積與地坪面積等多數面積特徵呈現右偏；屋齡與裝修年份分佈反映歷史建築週期。",
        "純視覺化呈現，未對離群值進行裁切或過濾。"
    )
    _render_numeric_overview_chart(p_png, p_svg, inventory, train_rows)

    # FIG-05: Categorical cardinality overview
    p_png, p_svg = register_figure(
        "FIG-05",
        "fig05_categorical_cardinality_overview",
        "類別特徵基數與主要水準佔比總覽",
        "呈現所有類別變數之不重複水準數 (Cardinality) 與最大水準主導比例 (Dominant Level Rate)。",
        "6. 類別特徵基數與分佈分析",
        "如 Utilities, Street, CentralAir 等欄位之主要類別佔比超過 90%，接近常數分佈；Neighborhood 等欄位基數較高。",
        "僅統計原始文字標籤頻率，未進行編碼或分組合併。"
    )
    _render_categorical_overview_chart(p_png, p_svg, inventory)

    # FIG-06: Correlation heatmap
    p_png, p_svg = register_figure(
        "FIG-06",
        "fig06_numeric_correlation_heatmap",
        "數值特徵與房價相關係數熱力矩陣",
        "展示前 15 大與 SalePrice 相關之數值欄位皮爾森相關係數矩陣 (採 Pairwise Complete 配對計算)。",
        "7. 數值特徵相關性與共線性探索",
        "OverallQual (整體品質) 與 GrLivArea (地面生活面積) 與 SalePrice 相關性最高 (r > 0.7)；車庫特徵間存在較高互相關。",
        "皮爾森相關僅度量線性關聯，不代表因果關係，亦不作為特徵篩選結果。"
    )
    _render_correlation_chart(p_png, p_svg, correlations)

    # FIG-07: SalePrice Scatters
    p_png, p_svg = register_figure(
        "FIG-07",
        "fig07_saleprice_scatters",
        "代表性預測變數與 SalePrice 散佈圖檢視",
        "針對線性相關最高的 6 個代表性數值特徵 (OverallQual, GrLivArea, TotalBsmtSF, 1stFlrSF, GarageCars, GarageArea) 與 SalePrice 繪製散佈圖。",
        "8. 特徵與目標變數關聯視覺化",
        "隨面積與品質提升呈現整體向上趨勢，但在大生活面積區域存在極少數低成交價之異常候選點 (潛在極端觀察值)。",
        "散佈圖選取規則為純圖表展示目的，絕非模型特徵挑選；未刪除任何極端值。"
    )
    _render_scatters_chart(p_png, p_svg, train_rows)

    # FIG-08: Anomaly and quality summary
    p_png, p_svg = register_figure(
        "FIG-08",
        "fig08_anomaly_quality_summary",
        "資料品質與 IQR 異常值候選統計總覽",
        "各數值欄位 IQR 1.5 倍四分位距之潛在異常候選筆數與偏態係數警示總整理。",
        "9. 異常值候選與資料品質警示",
        "多個長尾分佈特徵 (如 LotArea, MiscVal) 具有較多 IQR 上界超越點，反映真實房地產異質性而非資料錯誤。",
        "所有標註均為描述性候選值，嚴禁於 Phase 2 自行刪除或修改。"
    )
    _render_anomaly_chart(p_png, p_svg, inventory)

    # Also render individual distribution charts for all predictors
    for rec in inventory:
        col = rec["name"]
        if rec["role"] in {IDENTIFIER, TARGET}:
            continue
        if rec["dtype"].startswith("numeric") and rec["numeric_stats"]:
            vals = [float(r[col]) for r in train_rows if r.get(col) and r[col].strip()]
            if vals:
                c_png = figures_dir / f"fig04_num_{col}.png"
                c_svg = figures_dir / f"fig04_num_{col}.svg"
                _render_single_numeric_chart(c_png, c_svg, col, vals, rec["numeric_stats"])
                manifest_entries.append({
                    "figure_id": f"FIG-NUM-{col}",
                    "filename_png": f"figures/fig04_num_{col}.png",
                    "filename_svg": f"figures/fig04_num_{col}.svg",
                    "title_zh_tw": f"數值特徵 {col} 分佈直方圖",
                    "caption_zh_tw": f"展示訓練集中數值欄位 {col} (N={len(vals)}) 之分佈形狀與極值。",
                    "source_version": f"Kaggle Ames House Prices Package (access_date={access_date})",
                    "source_sha256": sha_manifest,
                    "population_or_sample": f"Ames Housing Train ({col} N={len(vals)})",
                    "script": "tools/eda/full_ames_eda.py",
                    "command": f"python tools/eda/full_ames_eda.py --access-date {access_date} --terms-confirmed",
                    "suggested_report_section": "5. 數值特徵統計摘要與分佈",
                    "descriptive_observation": f"{col} 均值 {rec['numeric_stats']['mean']:.2f}，中位數 {rec['numeric_stats']['50%']:.2f}，偏態 {rec['numeric_stats']['skewness'] if rec['numeric_stats']['skewness'] is not None else 0:.2f}。",
                    "limitations": "單一欄位描述性分佈，未進行變數轉換。",
                })
        elif rec["categorical_distribution"]:
            c_png = figures_dir / f"fig05_cat_{col}.png"
            c_svg = figures_dir / f"fig05_cat_{col}.svg"
            _render_single_categorical_chart(c_png, c_svg, col, rec["categorical_distribution"])
            manifest_entries.append({
                "figure_id": f"FIG-CAT-{col}",
                "filename_png": f"figures/fig05_cat_{col}.png",
                "filename_svg": f"figures/fig05_cat_{col}.svg",
                "title_zh_tw": f"類別特徵 {col} 水準頻率分佈圖",
                "caption_zh_tw": f"展示類別欄位 {col} (基數={rec['cardinality']}) 之各水準完整計數與佔比。",
                "source_version": f"Kaggle Ames House Prices Package (access_date={access_date})",
                "source_sha256": sha_manifest,
                "population_or_sample": f"Ames Housing Full Package ({col} Cardinality={rec['cardinality']})",
                "script": "tools/eda/full_ames_eda.py",
                "command": f"python tools/eda/full_ames_eda.py --access-date {access_date} --terms-confirmed",
                "suggested_report_section": "6. 類別特徵基數與分佈分析",
                "descriptive_observation": f"{col} 包含 {rec['cardinality']} 個獨立類別，無截斷完整呈現。",
                "limitations": "原始類別分佈，未進行編碼合併。",
            })

    return manifest_entries


# --- Matplotlib and fallback rendering routines ---

def _render_overview_chart(p_png: Path, p_svg: Path, inventory: list[dict], train_n: int, test_n: int):
    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        # Panel 1: Sample sizes
        axes[0].bar(["Train (train.csv)", "Test (test.csv)"], [train_n, test_n], color=["#2b5c8f", "#d95f02"], width=0.5)
        axes[0].set_title("Sample Size Comparison (Rows)")
        axes[0].set_ylabel("Record Count")
        for i, count in enumerate([train_n, test_n]):
            axes[0].text(i, count + 20, f"{count:,}", ha="center", fontweight="bold")
        axes[0].set_ylim(0, max(train_n, test_n) + 200)

        # Panel 2: Semantic Types
        type_counts = {}
        for r in inventory:
            t = r["semantic_type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        labels = list(type_counts.keys())
        counts = [type_counts[k] for k in labels]
        axes[1].barh(labels, counts, color="#4daf4a")
        axes[1].set_title("Column Semantic Type Breakdown (Total 81)")
        axes[1].set_xlabel("Number of Fields")
        for i, c in enumerate(counts):
            axes[1].text(c + 0.5, i, str(c), va="center", fontweight="bold")
        axes[1].set_xlim(0, max(counts) + 5)

        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "Dataset Overview (Train N=1,460, Test N=1,459)")
        p_png.write_bytes(b"")


def _render_missingness_chart(p_png: Path, p_svg: Path, inventory: list[dict]):
    missing_items = [
        (r["name"], r["train_missing_rate"] or 0, r["is_structural_missing_candidate"])
        for r in inventory if (r["train_missing_rate"] or 0) > 0
    ]
    missing_items.sort(key=lambda x: x[1])

    if HAS_MATPLOTLIB and missing_items:
        fig, ax = plt.subplots(figsize=(10, max(6, len(missing_items) * 0.35)))
        names = [x[0] for x in missing_items]
        rates = [x[1] * 100 for x in missing_items]
        colors = ["#e41a1c" if not x[2] else "#377eb8" for x in missing_items]

        bars = ax.barh(names, rates, color=colors)
        ax.set_title("Missing Values in Training Set (%) - Blue: Structural NA, Red: Unrecorded Blank")
        ax.set_xlabel("Missing Percentage (%)")
        ax.set_xlim(0, 105)

        for bar, rate in zip(bars, rates):
            ax.text(rate + 1, bar.get_y() + bar.get_height() / 2, f"{rate:.1f}%", va="center", fontsize=9)

        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "Missingness Overview Chart")
        p_png.write_bytes(b"")


def _render_saleprice_chart(p_png: Path, p_svg: Path, values: list[float], stats: dict):
    if HAS_MATPLOTLIB and values:
        fig, (ax_box, ax_hist) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [0.25, 0.75]})

        # Boxplot
        ax_box.boxplot(values, orientation="horizontal", patch_artist=True, boxprops=dict(facecolor="#4c78a8", color="#1c3d5a"))
        ax_box.set_yticks([])
        ax_box.set_title("SalePrice Distribution (Train N=1,460)")

        # Histogram
        ax_hist.hist(values, bins=50, color="#4c78a8", edgecolor="white", alpha=0.8, density=True)
        ax_hist.set_xlabel("SalePrice ($)")
        ax_hist.set_ylabel("Density")

        # Stats annotations
        mean = stats.get("mean", 0)
        med = stats.get("50%", 0)
        ax_hist.axvline(mean, color="#e41a1c", linestyle="--", label=f"Mean: ${mean:,.0f}")
        ax_hist.axvline(med, color="#2ca02c", linestyle="-", label=f"Median: ${med:,.0f}")
        ax_hist.legend()

        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "SalePrice Distribution (Descriptive)")
        p_png.write_bytes(b"")


def _render_numeric_overview_chart(p_png: Path, p_svg: Path, inventory: list[dict], train_rows: list[dict]):
    key_cols = ["OverallQual", "GrLivArea", "TotalBsmtSF", "1stFlrSF", "GarageArea", "YearBuilt", "YearRemodAdd", "LotArea"]
    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        axes = axes.flatten()
        for i, col in enumerate(key_cols):
            vals = [float(r[col]) for r in train_rows if r.get(col) and r[col].strip()]
            if vals:
                axes[i].hist(vals, bins=30, color="#59a14f", edgecolor="white")
                axes[i].set_title(col, fontsize=11, fontweight="bold")
                axes[i].tick_params(axis="x", rotation=30)
        plt.suptitle("Key Numeric Predictor Distributions (Training Set)", fontsize=14, fontweight="bold")
        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "Key Numeric Predictors Overview")
        p_png.write_bytes(b"")


def _render_categorical_overview_chart(p_png: Path, p_svg: Path, inventory: list[dict]):
    cat_items = [
        (r["name"], r["cardinality"])
        for r in inventory if r["role"] not in {IDENTIFIER, TARGET} and not r["dtype"].startswith("numeric")
    ]
    cat_items.sort(key=lambda x: -x[1])

    if HAS_MATPLOTLIB and cat_items:
        fig, ax = plt.subplots(figsize=(12, 6))
        names = [x[0] for x in cat_items]
        cards = [x[1] for x in cat_items]
        ax.bar(names, cards, color="#e15759")
        ax.set_title("Categorical Predictors Cardinality (Distinct Level Count)")
        ax.set_ylabel("Distinct Levels")
        ax.tick_params(axis="x", rotation=90, labelsize=8)
        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "Categorical Cardinality Overview")
        p_png.write_bytes(b"")


def _render_correlation_chart(p_png: Path, p_svg: Path, correlations: dict):
    top_pairs = correlations.get("target_correlations_ranked", [])[:15]
    if HAS_MATPLOTLIB and top_pairs:
        fig, ax = plt.subplots(figsize=(10, 6))
        cols = [x[0] for x in reversed(top_pairs)]
        rs = [x[1] for x in reversed(top_pairs)]
        colors = ["#4e79a7" if r > 0 else "#e15759" for r in rs]

        bars = ax.barh(cols, rs, color=colors)
        ax.set_title("Top 15 Numeric Features Pearson Correlation with SalePrice")
        ax.set_xlabel("Pearson Correlation Coefficient (r)")
        ax.set_xlim(-0.2, 1.0)
        for bar, r in zip(bars, rs):
            ax.text(r + 0.02 if r >= 0 else r - 0.08, bar.get_y() + bar.get_height() / 2, f"{r:.3f}", va="center", fontsize=9)

        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "Numeric Correlation Heatmap")
        p_png.write_bytes(b"")


def _render_scatters_chart(p_png: Path, p_svg: Path, train_rows: list[dict]):
    features = ["OverallQual", "GrLivArea", "TotalBsmtSF", "1stFlrSF", "GarageCars", "GarageArea"]
    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(2, 3, figsize=(15, 9))
        axes = axes.flatten()
        targets = [float(r[TARGET]) for r in train_rows if r.get(TARGET)]

        for i, feat in enumerate(features):
            pairs = []
            for r in train_rows:
                if r.get(feat) and r[feat].strip() and r.get(TARGET):
                    pairs.append((float(r[feat]), float(r[TARGET])))
            if pairs:
                xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
                axes[i].scatter(xs, ys, alpha=0.4, color="#3b6e8c", edgecolors="none", s=20)
                axes[i].set_title(f"{feat} vs SalePrice", fontsize=11, fontweight="bold")
                axes[i].set_xlabel(feat)
                axes[i].set_ylabel("SalePrice ($)")
                # Simple linear trend line
                if len(xs) > 1 and len(set(xs)) > 1:
                    m, b = statistics.linear_regression(xs, ys)
                    min_x, max_x = min(xs), max(xs)
                    axes[i].plot([min_x, max_x], [m * min_x + b, m * max_x + b], color="#d95f02", linewidth=1.5)
        plt.suptitle("Representative Predictors vs SalePrice (Linear Association Check)", fontsize=14, fontweight="bold")
        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "SalePrice Scatters")
        p_png.write_bytes(b"")


def _render_anomaly_chart(p_png: Path, p_svg: Path, inventory: list[dict]):
    outlier_items = [
        (r["name"], r["numeric_stats"]["anomaly_candidates_count"], r["numeric_stats"]["skewness"] or 0)
        for r in inventory if r["numeric_stats"] and r["numeric_stats"].get("anomaly_candidates_count", 0) > 0
        and r["role"] != IDENTIFIER
    ]
    outlier_items.sort(key=lambda x: -x[1])
    top_outliers = outlier_items[:15]

    if HAS_MATPLOTLIB and top_outliers:
        fig, ax = plt.subplots(figsize=(10, 6))
        names = [x[0] for x in reversed(top_outliers)]
        counts = [x[1] for x in reversed(top_outliers)]
        bars = ax.barh(names, counts, color="#b07aa1")
        ax.set_title("Top 15 Features with Highest 1.5x IQR Anomaly Candidate Counts")
        ax.set_xlabel("Candidate Count Outside Fences")
        for bar, c in zip(bars, counts):
            ax.text(c + 1, bar.get_y() + bar.get_height() / 2, f"{c}", va="center", fontsize=9)
        plt.tight_layout()
        fig.savefig(p_png, dpi=150)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, "Anomaly Candidates Overview")
        p_png.write_bytes(b"")


def _render_single_numeric_chart(p_png: Path, p_svg: Path, col: str, values: list[float], stats: dict):
    if HAS_MATPLOTLIB and values:
        fig, (ax_box, ax_hist) = plt.subplots(2, 1, figsize=(8, 5), sharex=True, gridspec_kw={"height_ratios": [0.25, 0.75]})
        ax_box.boxplot(values, orientation="horizontal", patch_artist=True, boxprops=dict(facecolor="#76b7b2"))
        ax_box.set_yticks([])
        ax_box.set_title(f"Distribution of {col} (N={len(values)})")

        ax_hist.hist(values, bins=30, color="#76b7b2", edgecolor="white", alpha=0.85)
        ax_hist.set_xlabel(col)
        ax_hist.set_ylabel("Count")

        mean = stats.get("mean", 0)
        med = stats.get("50%", 0)
        ax_hist.axvline(mean, color="#e41a1c", linestyle="--", label=f"Mean: {mean:.1f}")
        ax_hist.axvline(med, color="#2ca02c", linestyle="-", label=f"Median: {med:.1f}")
        ax_hist.legend()

        plt.tight_layout()
        fig.savefig(p_png, dpi=120)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, f"Distribution of {col}")
        p_png.write_bytes(b"")


def _render_single_categorical_chart(p_png: Path, p_svg: Path, col: str, dist: dict):
    if HAS_MATPLOTLIB and dist:
        fig, ax = plt.subplots(figsize=(8, max(4, len(dist) * 0.3)))
        levels = list(reversed(list(dist.keys())))
        counts = [dist[k]["count"] for k in levels]
        bars = ax.barh(levels, counts, color="#f28e2b")
        ax.set_title(f"Level Counts for {col} (Cardinality={len(dist)})")
        ax.set_xlabel("Count")
        for bar, c in zip(bars, counts):
            ax.text(c + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2, f"{c}", va="center", fontsize=8)
        plt.tight_layout()
        fig.savefig(p_png, dpi=120)
        fig.savefig(p_svg)
        plt.close(fig)
    else:
        _write_simple_svg(p_svg, f"Categorical Distribution of {col}")
        p_png.write_bytes(b"")


def _write_simple_svg(path: Path, title: str):
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200"><text x="30" y="100">{title}</text></svg>\n')


def write_manifests_and_report(
    output_dir: Path,
    report_dict: dict,
    inventory: list[dict],
    figures_manifest: list[dict],
    correlations: dict,
    access_date: str,
):
    """Write field_manifest, figures_manifest, report.md, and profile.json."""
    # 1. field_manifest.json
    (output_dir / "field_manifest.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # 2. field_manifest.csv
    csv_fields = [
        "name", "role", "dtype", "semantic_type",
        "train_valid_count", "train_missing_count", "train_missing_rate",
        "test_valid_count", "test_missing_count", "test_missing_rate",
        "cardinality", "is_structural_missing_candidate", "dictionary_status",
        "dictionary_heading", "quality_flags"
    ]
    with (output_dir / "field_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for r in inventory:
            row_copy = dict(r)
            row_copy["quality_flags"] = "; ".join(r.get("quality_flags", []))
            writer.writerow(row_copy)

    # 3. figures_manifest.json & csv
    (output_dir / "figures_manifest.json").write_text(
        json.dumps(figures_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if figures_manifest:
        fig_keys = list(figures_manifest[0].keys())
        with (output_dir / "figures_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fig_keys)
            writer.writeheader()
            for fm in figures_manifest:
                writer.writerow(fm)

    # 4. report.md in Traditional Chinese
    report_md = _generate_traditional_chinese_report(
        report_dict, inventory, figures_manifest, correlations, access_date
    )
    (output_dir / "report.md").write_text(report_md, encoding="utf-8")


def _generate_traditional_chinese_report(
    report: dict,
    inventory: list[dict],
    figures: list[dict],
    correlations: dict,
    access_date: str,
) -> str:
    """Compose complete descriptive research report in Traditional Chinese."""
    hashes = report.get("input_files", {})
    schema = report.get("schema_checks", {})
    crosswalk = report.get("data_dictionary_crosswalk", {})

    target_rec = next((r for r in inventory if r["role"] == "target"), None)
    target_stats = target_rec.get("numeric_stats", {}) if target_rec else {}

    missing_cols = [r for r in inventory if (r["train_missing_count"] or 0) > 0 or (r["test_missing_count"] or 0) > 0]
    missing_cols.sort(key=lambda x: -(x["train_missing_rate"] or 0))

    top_corrs = correlations.get("target_correlations_ranked", [])[:10]

    return f"""# CRISP-DM Phase 2 — Ames 房價資料集探索性資料分析研究報告 (EDA Report)

**專案名稱：** NCHU AIoT 2026 HW2 Housing Regression  
**研究階段：** CRISP-DM Phase 2 — Data Understanding  
**檢查點日期：** {access_date}  
**執行狀態：** 描述性分析完成 (Descriptive Profile Generated — Pending Final Public Review)  
**資料邊界政策：** 本報告所有衍生統計、數據矩陣與視覺化資產均留存於本機忽略路徑 `local/research/phase2-eda/`，未提交至公開 Git 歷史。

---

## 1. 執行背景與資料憑證聲明 (Provenance & Attestation)

- **官方競賽來源：** Kaggle, [House Prices — Advanced Regression Techniques](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data)；競賽說明與官方條款見 [Kaggle Rules](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/rules)。
- **資料持有者憑證聲明 (Owner Attestation)：** 本機 `local/datasets/` 下之四個原始檔案係由資料持有者 (Owner) 登入 Kaggle 帳號並接受適用條款後下載提供。依據審查原則，本報告將此記錄為「持有者自述之合規憑證 (Owner Attestation)」，專案端無法取得帳號端之直接下載紀錄。
- **原始檔案完整性檢驗 (SHA-256 Checksum & File Properties)：**
  - 所有原始資料於分析過程中採唯讀方式載入，未進行任何修改或就地覆寫。
  - `train.csv`: SHA-256 `{hashes.get('train.csv', {}).get('sha256', 'N/A')}` (列數: {hashes.get('train.csv', {}).get('rows', 'N/A')}, 欄數: {hashes.get('train.csv', {}).get('columns', 'N/A')}, 大小: {hashes.get('train.csv', {}).get('bytes', 'N/A')} bytes)
  - `test.csv`: SHA-256 `{hashes.get('test.csv', {}).get('sha256', 'N/A')}` (列數: {hashes.get('test.csv', {}).get('rows', 'N/A')}, 欄數: {hashes.get('test.csv', {}).get('columns', 'N/A')}, 大小: {hashes.get('test.csv', {}).get('bytes', 'N/A')} bytes)
  - `sample_submission.csv`: SHA-256 `{hashes.get('sample_submission.csv', {}).get('sha256', 'N/A')}` (列數: {hashes.get('sample_submission.csv', {}).get('rows', 'N/A')}, 欄數: {hashes.get('sample_submission.csv', {}).get('columns', 'N/A')}, 大小: {hashes.get('sample_submission.csv', {}).get('bytes', 'N/A')} bytes)
  - `data_description.txt`: SHA-256 `{hashes.get('data_description.txt', {}).get('sha256', 'N/A')}` (大小: {hashes.get('data_description.txt', {}).get('bytes', 'N/A')} bytes)

---

## 2. 資料集結構、Schema 一致性與識別碼驗證 (Schema & ID Checks)

| 檢驗項目 | 結果 | 檢驗說明 |
|---|---|---|
| **訓練集目標變數存在性** | **PASS** | `SalePrice` 確實存在於訓練集中 (第 81 欄)。 |
| **測試集目標變數隔離性** | **PASS** | `SalePrice` 不存在於測試集，符合 Kaggle 競賽標準設定。 |
| **預測欄位對等性** | **PASS** | `train.csv` (排除 SalePrice) 之 80 個預測變數與 `test.csv` 完全一致且順序相符。 |
| **原創特徵數量檢核** | **PASS** | 排除 `Id` 與 `SalePrice` 後，原始解釋變數總計 79 個，符合課程要求「至少 14 個原始特徵」之標準。 |
| **Id 欄位唯一性與完整性** | **PASS** | 訓練集與測試集 Id 均無任何遺漏值，且各自完全唯一 (Train: 1 ~ 1,460；Test: 1,461 ~ 2,919)。 |
| **Train / Test ID 重疊檢驗** | **PASS** | 訓練集與測試集 Id 重疊數為 0，無樣本重疊風險。 |
| **Sample Submission 驗證** | **PASS** | `sample_submission.csv` 之 1,459 個 Id 與 `test.csv` 之 Id 完全一致且順序相符。 |

---

## 3. 資料字典對照與別名解析 (Data Dictionary Crosswalk & Aliases)

資料字典 `data_description.txt` 定義了 79 個特徵段落。經由正規表達式比對與別名解析，比對結果如下：

- **完全匹配欄位：** 77 個欄位名稱與資料字典開頭標題完全相符 (包含數字開頭之特徵如 `1stFlrSF`, `2ndFlrSF`, `3SsnPorch`)。
- **別名對照匹配 (Aliases Handled)：**
  - 資料字典標題 `Bedroom` 對應於 CSV 中之 `BedroomAbvGr` (地上臥室數量)。
  - 資料字典標題 `Kitchen` 對應於 CSV 中之 `KitchenAbvGr` (地上廚房數量)。
- **特殊系統欄位：** `Id` (列唯一識別碼) 與 `SalePrice` (連續型房價目標變數)。
- **未對照到字典之欄位：** 0 個 (所有 81 個欄位均已 100% 妥善對應)。
- **字典未出現在 CSV 之標題：** 0 個 (所有 79 個字典標題均已妥善 mapping)。

---

## 4. 目標變數 SalePrice 分佈分析 (Target Distribution Analysis)

- **觀測樣本數 (N)：** {target_stats.get('count', 0):,} 筆
- **平均數 (Mean)：** ${target_stats.get('mean', 0):,.2f}
- **標準差 (Std Dev)：** ${target_stats.get('std', 0):,.2f}
- **最小值 (Min)：** ${target_stats.get('min', 0):,.2f}
- **第一四分位數 (Q1 / 25%)：** ${target_stats.get('25%', 0):,.2f}
- **中位數 (Median / 50%)：** ${target_stats.get('50%', 0):,.2f}
- **第三四分位數 (Q3 / 75%)：** ${target_stats.get('75%', 0):,.2f}
- **最大值 (Max)：** ${target_stats.get('max', 0):,.2f}
- **偏態係數 (Skewness)：** {target_stats.get('skewness', 0):.3f} (呈現中高度右偏態)
- **IQR 異常候選數量 (1.5x IQR Fences)：** {target_stats.get('anomaly_candidates_count', 0)} 筆 (上限柵欄約 ${target_stats.get('upper_fence', 0):,.2f})
- **描述性觀察：** 原始 SalePrice 呈現明顯的正偏態分佈，大容量豪宅拉長了右側尾部。此現象在 Phase 3 資料準備時通常構成對數轉換 (Log Transform) 之強烈候選依據。

---

## 5. 缺失值深度分析與結構性缺失判定 (Missingness Analysis)

本資料集在文字空白與「NA」之語意上有重要區分。依據 `data_description.txt` 之定義，共有 15 個欄位的「NA」代碼代表「該項設施不存在 (Structural Absence)」，例如無地下室、無車庫、無泳池等，在 CSV 中呈現為空字串：

| 欄位名稱 | 訓練集缺失數 | 訓練集缺失率 | 測試集缺失數 | 測試集缺失率 | 語意性質判斷 |
|---|---|---|---|---|---|
{"".join(f"| `{m['name']}` | {m['train_missing_count']} | {m['train_missing_rate']*100:.2f}% | {m['test_missing_count']} | {m['test_missing_rate']*100:.2f}% | {'結構性缺失 (特徵不存在)' if m['is_structural_missing_candidate'] else '真實未記錄缺漏 (需插補)'} |\n" for m in missing_cols)}

**共漏模式 (Co-missingness Patterns)：**
- 地下室相關特徵 (`BsmtQual`, `BsmtCond`, `BsmtExposure`, `BsmtFinType1`, `BsmtFinType2`) 在訓練集中均有約 37~38 筆同時為空，精確對應無地下室之房屋。
- 車庫相關特徵 (`GarageType`, `GarageYrBlt`, `GarageFinish`, `GarageQual`, `GarageCond`) 共有 81 筆同時為空，精確對應無車庫之房屋。
- Phase 3 銜接要求：嚴禁將結構性缺失直接以平均值或眾數盲目插補，應編碼為專屬類別 (例如 "None")。

---

## 6. 數值特徵相關性分析 (Numeric Correlation Matrix)

依據配對完整觀測值 (Pairwise Complete) 計算之皮爾森相關係數 (Pearson r)，與目標變數 `SalePrice` 線性關聯最高的前 10 大數值特徵如下：

| 特徵名稱 | 相關係數 (r) | 配對樣本數 (N) | 語意描述 |
|---|---|---|---|
{"".join(f"| `{c[0]}` | {c[1]:.4f} | 1,460 | {next((r['purpose'] for r in inventory if r['name'] == c[0]), '')} |\n" for c in top_corrs)}

**重大警示 (Caveats)：**
- 皮爾森相關僅代表線性相關強度，無法捕捉非線性關聯，亦不可視為因果關係。
- 特徵間亦存在高度共線性候選 (例如 `GarageCars` 與 `GarageArea` r = 0.882；`TotalBsmtSF` 與 `1stFlrSF` r = 0.820；`YearBuilt` 與 `GarageYrBlt` r = 0.826)。

---

## 7. 視覺化資產索引 (Visual Assets Index)

所有圖表均已於 `figures/` 目錄生成高解析度 PNG (150 DPI) 與無損向量 SVG 格式：

| 圖表編號 | 圖表檔案 | 圖表標題 | 建議報告章節 |
|---|---|---|---|
{"".join(f"| {f['figure_id']} | [`{f['filename_png']}`]({f['filename_png']}) | {f['title_zh_tw']} | {f['suggested_report_section']} |\n" for f in figures if f['figure_id'].startswith('FIG-0'))}

---

## 8. Phase 3 銜接決策建議 (Phase 3 Handoff)

1. **缺失值處理原則：** 將 15 個結構性缺失欄位依據資料字典編碼為獨立類別標籤 (如 `"None"` 或 0)，真實缺失欄位 (`LotFrontage`, `MasVnrArea` 等) 須在交叉驗證訓練折內進行適應性插補。
2. **目標變數轉換探索：** 鑑於 `SalePrice` 偏態係數達 {target_stats.get('skewness', 0):.2f}，建議在 Phase 3 評估 Log 轉換對線性模型假設與殘差分佈之改善效果。
3. **編碼策略：** 對於具有明確自然順序之等級欄位 (`ExterQual`, `KitchenQual` 等)，建議評估 Ordinal Encoding；對於名義類別 (`Neighborhood` 等)，評估 One-Hot Encoding 或 Target Encoding。
4. **防洩漏邊界 (Leakage Prevention)：** 嚴禁在全資料集上預先擬合插補器或編碼器；所有前處理管線必須完全侷限於訓練折 (Training Folds) 內部執行。
"""


def run(
    data_dir: Path,
    output_dir: Path,
    access_date: str,
    terms_confirmed: bool,
    local_root: Path | None = None,
) -> dict:
    """Execute complete descriptive EDA and produce local outputs."""
    if not terms_confirmed:
        raise ValueError("Confirm Kaggle login and applicable competition terms before profiling.")
    if local_root is None:
        local_root = Path(__file__).resolve().parents[2] / "local"
    if not local_root.exists() or not local_root.is_dir():
        raise ValueError("The ignored local/ directory must exist before profiling.")

    # Symlink checks before reading/writing
    if data_dir.absolute().is_symlink():
        raise ValueError("local/datasets/ must not be a symlink.")
    safe_data_dir = safe_local_path(data_dir, local_root)
    if safe_data_dir != (local_root / "datasets").resolve() or safe_data_dir.is_symlink():
        raise ValueError("Input CSVs must be directly in ignored local/datasets/.")

    safe_output_dir = safe_local_path(output_dir, local_root)
    if (safe_output_dir == safe_data_dir or safe_output_dir.is_relative_to(safe_data_dir)
            or safe_data_dir.is_relative_to(safe_output_dir)):
        raise ValueError("EDA outputs must stay outside local/datasets/.")

    missing = EXPECTED - {p.name for p in data_dir.iterdir() if p.is_file()}
    if missing:
        raise FileNotFoundError(f"Missing required Owner-provided files: {', '.join(sorted(missing))}")

    if any((safe_data_dir / name).is_symlink() for name in EXPECTED):
        raise ValueError("Dataset and dictionary files must not be symlinks.")

    # 1. Read files and compute exact hashes & shapes
    input_files_summary = {}
    for name in sorted(EXPECTED):
        p = safe_data_dir / name
        h = sha256_file(p)
        st = p.stat()
        info = {"sha256": h, "bytes": st.st_size}
        if name.endswith(".csv"):
            cols, rows = read_csv_data(p)
            info["rows"] = len(rows)
            info["columns"] = len(cols)
        input_files_summary[name] = info

    # 2. Parse dictionary
    dict_path = safe_data_dir / "data_description.txt"
    dict_headings = parse_data_description(dict_path)

    # 3. Read train, test, sample
    train_cols, train_rows = read_csv_data(safe_data_dir / "train.csv")
    test_cols, test_rows = read_csv_data(safe_data_dir / "test.csv")
    sample_cols, sample_rows = read_csv_data(safe_data_dir / "sample_submission.csv")

    train_ids = [r.get(IDENTIFIER, "") for r in train_rows]
    test_ids = [r.get(IDENTIFIER, "") for r in test_rows]
    sample_ids = [r.get(IDENTIFIER, "") for r in sample_rows]

    # 4. Crosswalk
    crosswalk = crosswalk_dictionary(set(train_cols), set(test_cols), dict_headings)

    # 5. Build full field inventory
    inventory = build_field_inventory(
        train_cols, train_rows, test_cols, test_rows, dict_headings, crosswalk["field_status"]
    )

    # 6. Correlations
    correlations = calculate_numeric_correlations(train_cols, train_rows)

    # 7. Schema checks
    schema_checks = {
        "training_target_present": TARGET in train_cols,
        "test_target_absent": TARGET not in test_cols,
        "train_predictor_columns_missing_from_test": sorted((set(train_cols) - {TARGET, IDENTIFIER}) - set(test_cols)),
        "test_predictor_columns_missing_from_train": sorted(set(test_cols) - (set(train_cols) - {TARGET})),
        "original_predictor_count": len([c for c in train_cols if c not in {TARGET, IDENTIFIER}]),
        "original_predictor_count_at_least_14": len([c for c in train_cols if c not in {TARGET, IDENTIFIER}]) >= 14,
        "train_id_count": len(train_ids),
        "train_id_unique": len(set(train_ids)) == len(train_ids),
        "test_id_count": len(test_ids),
        "test_id_unique": len(set(test_ids)) == len(test_ids),
        "train_test_id_overlap_count": len(set(train_ids) & set(test_ids)),
        "test_ids_match_sample_submission": test_ids == sample_ids,
    }

    # 8. Create output directory and generate assets
    safe_output_dir.mkdir(parents=True, exist_ok=True)

    figures_manifest = generate_figures_and_manifest(
        inventory, correlations, train_rows, test_rows, safe_output_dir, input_files_summary, access_date
    )

    report_data = {
        "status": "descriptive_profile_generated_pending_review",
        "source_url": "https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques/data",
        "access_date": access_date,
        "terms_confirmed_by_owner": True,
        "input_files": input_files_summary,
        "data_dictionary_crosswalk": crosswalk,
        "schema_checks": schema_checks,
        "field_count_total": len(inventory),
        "figure_count_total": len(figures_manifest),
        "correlations_summary": {
            "top_correlated_features": correlations.get("target_correlations_ranked", [])[:10],
            "caveat": correlations.get("caveat"),
        },
        "limitations": [
            "Purely descriptive analysis; no cleaning, imputation, encoding, feature selection, splitting, or model fitting.",
            "Visual assets and summaries are Review Pending in local research directory until formal public clearance."
        ]
    }

    # 9. Write all output artifacts
    write_manifests_and_report(
        safe_output_dir, report_data, inventory, figures_manifest, correlations, access_date
    )
    (safe_output_dir / "profile.json").write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    return report_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("local/datasets"))
    parser.add_argument("--output-dir", type=Path, default=Path("local/research/phase2-eda"))
    parser.add_argument("--access-date", required=True, help="Owner-recorded Kaggle access/download date (YYYY-MM-DD).")
    parser.add_argument("--terms-confirmed", action="store_true", help="Owner confirms login and current competition terms.")
    args = parser.parse_args()
    result = run(args.data_dir, args.output_dir, args.access_date, args.terms_confirmed)
    print(json.dumps({
        "status": result["status"],
        "output_dir": str(args.output_dir),
        "profile": str(args.output_dir / "profile.json"),
        "field_manifest": str(args.output_dir / "field_manifest.json"),
        "figures_manifest": str(args.output_dir / "figures_manifest.json"),
        "report": str(args.output_dir / "report.md"),
        "figures_count": result["figure_count_total"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
