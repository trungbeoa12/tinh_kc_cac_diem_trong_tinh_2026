#!/usr/bin/env python3
"""Build 20260504_ver2 from stable 3-period pairs and recrawl results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


COMPARE_DIR = config.PROJECT_ROOT / "outputs" / "compare_distance_3_periods"
DEFAULT_SAMPLE = config.PROJECT_ROOT / "data_20260504_ver2" / "20260504.xlsx"
DEFAULT_OUTPUT = config.PROJECT_ROOT / "data_20260504_ver2" / "20260504_ver2.xlsx"
DEFAULT_AUDIT = COMPARE_DIR / "build_20260504_ver2_summary.xlsx"

OUTPUT_COLUMNS = [
    "global_index",
    "original_excel_row",
    "ma_phong_ban_1",
    "ten_phong_ban_1",
    "kinh_do_1",
    "vi_do_1",
    "ma_phong_ban_2",
    "ten_phong_ban_2",
    "kinh_do_2",
    "vi_do_2",
    "khoang_cach_chim_bay",
    "tinh_thanh",
    "PART_ID",
    "row_in_part",
    "Khoảng cách đường bộ",
    "Khoảng cách đường bộ km",
    "thời gian",
    "source_output_file",
    "source_kind",
    "crawl_status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-dir", type=Path, default=COMPARE_DIR)
    parser.add_argument("--sample-file", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-file", type=Path, default=DEFAULT_AUDIT)
    return parser.parse_args()


def normalize_code(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text.replace(".0", "").isdigit():
        return text[:-2]
    return text


def make_pair_key(row: pd.Series) -> str:
    left = normalize_code(row["ma_phong_ban_1"])
    right = normalize_code(row["ma_phong_ban_2"])
    return "__".join(sorted([left, right]))


def read_required_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_excel(path)


def stable_to_output(khop: pd.DataFrame, khop_path: Path) -> pd.DataFrame:
    result = pd.DataFrame()
    for column in [
        "ma_phong_ban_1",
        "ten_phong_ban_1",
        "kinh_do_1",
        "vi_do_1",
        "ma_phong_ban_2",
        "ten_phong_ban_2",
        "kinh_do_2",
        "vi_do_2",
        "khoang_cach_chim_bay",
        "tinh_thanh",
    ]:
        result[column] = khop[column]

    result["Khoảng cách đường bộ"] = khop["distance_raw_20260504"]
    result["Khoảng cách đường bộ km"] = khop["distance_20260504"]
    result["thời gian"] = result["Khoảng cách đường bộ"].map(extract_duration_from_raw)
    result["source_output_file"] = str(khop_path.relative_to(config.PROJECT_ROOT))
    result["source_kind"] = "stable_matched_3_periods"
    result["crawl_status"] = "stable_3_periods"
    result["pair_key"] = khop["pair_key"]
    return result


def extract_duration_from_raw(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    lines = [line.strip() for line in str(value).splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[0]
    return pd.NA


def recrawl_to_output(recrawl: pd.DataFrame, source_path: Path) -> pd.DataFrame:
    result = pd.DataFrame()
    for column in [
        "ma_phong_ban_1",
        "ten_phong_ban_1",
        "kinh_do_1",
        "vi_do_1",
        "ma_phong_ban_2",
        "ten_phong_ban_2",
        "kinh_do_2",
        "vi_do_2",
        "khoang_cach_chim_bay",
        "tinh_thanh",
    ]:
        result[column] = recrawl[column]

    result["Khoảng cách đường bộ"] = recrawl["recrawl_raw_text"]
    result["Khoảng cách đường bộ km"] = recrawl["recrawl_distance_km"]
    result["thời gian"] = recrawl["recrawl_duration_text"]
    result["source_output_file"] = str(source_path.relative_to(config.PROJECT_ROOT))
    result["source_kind"] = "recrawl_compare_3_periods"
    result["crawl_status"] = recrawl["recrawl_status"].map(map_recrawl_status)
    result["pair_key"] = recrawl.apply(make_pair_key, axis=1)
    result["recrawl_status"] = recrawl["recrawl_status"]
    result["recrawl_attempts"] = recrawl["recrawl_attempts"]
    return result


def map_recrawl_status(value: object) -> str:
    status = "" if pd.isna(value) else str(value)
    if status == "OK":
        return "recrawled_ok"
    if "SUSPECT_DISTANCE" in status or "POSSIBLE_STALE_ROUTE" in status:
        return "recrawled_suspect"
    if status:
        return f"recrawled_{status.lower()}"
    return "recrawled_unknown"


def add_index_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy().reset_index(drop=True)
    result.insert(0, "global_index", range(len(result)))
    result.insert(1, "original_excel_row", result["global_index"] + 2)
    result["PART_ID"] = result["global_index"] // 100 + 1
    result["row_in_part"] = result["global_index"] % 100
    return result


def write_excel(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False, sheet_name="Sheet1")


def build_summary(
    output: pd.DataFrame,
    khop: pd.DataFrame,
    recrawl_frames: list[pd.DataFrame],
    duplicate_keys: pd.DataFrame,
    missing_current_pairs: pd.DataFrame,
) -> pd.DataFrame:
    recrawl = pd.concat(recrawl_frames, ignore_index=True) if recrawl_frames else pd.DataFrame()
    rows: list[dict[str, Any]] = [
        {"metric": "khop_3ky_rows", "value": len(khop)},
        {"metric": "recrawl_rows", "value": len(recrawl)},
        {"metric": "output_rows", "value": len(output)},
        {"metric": "output_unique_pair_keys", "value": output["pair_key"].nunique()},
        {"metric": "duplicate_pair_keys", "value": duplicate_keys["pair_key"].nunique() if len(duplicate_keys) else 0},
        {"metric": "missing_current_pairs_after_excluding_con_dao", "value": len(missing_current_pairs)},
        {"metric": "output_null_distance_km", "value": int(output["Khoảng cách đường bộ km"].isna().sum())},
    ]
    for status, count in output["crawl_status"].value_counts(dropna=False).items():
        rows.append({"metric": f"crawl_status::{status}", "value": int(count)})
    if len(recrawl):
        for status, count in recrawl["recrawl_status"].value_counts(dropna=False).items():
            rows.append({"metric": f"recrawl_status::{status}", "value": int(count)})
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    khop_path = args.compare_dir / "khop_3ky.xlsx"
    all_pairs_path = args.compare_dir / "all_pairs_from_branches_20260504.xlsx"
    excluded_path = args.compare_dir / "pairs_excluded_con_dao.xlsx"
    recrawl_paths = sorted((args.compare_dir / "recrawl_outputs").glob("batch_*/recrawl_results.xlsx"))

    if not recrawl_paths:
        raise FileNotFoundError(f"Không tìm thấy recrawl_results.xlsx trong {args.compare_dir / 'recrawl_outputs'}")

    sample = read_required_excel(args.sample_file)
    missing_sample_cols = [column for column in OUTPUT_COLUMNS if column not in sample.columns]
    if missing_sample_cols:
        raise ValueError(f"Sample file thiếu cột dự kiến: {missing_sample_cols}")

    khop = read_required_excel(khop_path)
    stable = stable_to_output(khop, khop_path)

    recrawl_frames: list[pd.DataFrame] = []
    for path in recrawl_paths:
        recrawl_df = read_required_excel(path)
        recrawl_frames.append(recrawl_df)

    recrawl_output = pd.concat(
        [recrawl_to_output(df, path) for df, path in zip(recrawl_frames, recrawl_paths)],
        ignore_index=True,
    )

    combined = pd.concat([stable, recrawl_output], ignore_index=True)
    combined["pair_key"] = combined.apply(make_pair_key, axis=1)
    duplicate_mask = combined["pair_key"].duplicated(keep=False)
    duplicate_keys = combined.loc[duplicate_mask].copy()
    if len(duplicate_keys):
        raise ValueError(f"Có trùng pair_key trong output: {duplicate_keys['pair_key'].nunique()} khóa")

    output = add_index_columns(combined)
    output = output.sort_values(["tinh_thanh", "ma_phong_ban_1", "ma_phong_ban_2"], kind="mergesort").reset_index(drop=True)
    output = add_index_columns(output.drop(columns=["global_index", "original_excel_row", "PART_ID", "row_in_part"]))

    output_for_excel = output[OUTPUT_COLUMNS].copy()
    write_excel(args.output_file, output_for_excel)

    all_pairs = read_required_excel(all_pairs_path) if all_pairs_path.exists() else pd.DataFrame()
    excluded = read_required_excel(excluded_path) if excluded_path.exists() else pd.DataFrame()
    current_expected = all_pairs.copy()
    if len(excluded) and "pair_key" in excluded.columns:
        current_expected = current_expected.loc[~current_expected["pair_key"].isin(set(excluded["pair_key"]))]

    output_keys = set(output["pair_key"])
    missing_current_pairs = (
        current_expected.loc[~current_expected["pair_key"].isin(output_keys)].copy()
        if len(current_expected) and "pair_key" in current_expected.columns
        else pd.DataFrame()
    )

    summary = build_summary(output, khop, recrawl_frames, duplicate_keys, missing_current_pairs)
    args.audit_file.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(args.audit_file) as writer:
        summary.to_excel(writer, index=False, sheet_name="summary")
        if len(missing_current_pairs):
            missing_current_pairs.to_excel(writer, index=False, sheet_name="missing_pairs")

    print("Build 20260504_ver2 completed")
    print(f"  Stable khop_3ky rows: {len(khop)}")
    print(f"  Recrawl rows: {sum(len(frame) for frame in recrawl_frames)}")
    print(f"  Output rows: {len(output_for_excel)}")
    print(f"  Output unique pair keys: {output['pair_key'].nunique()}")
    print(f"  Null distance km: {int(output_for_excel['Khoảng cách đường bộ km'].isna().sum())}")
    print(f"  Output file: {args.output_file}")
    print(f"  Audit file: {args.audit_file}")
    if len(missing_current_pairs):
        print(f"  WARNING: Missing current pairs after excluding Con Dao: {len(missing_current_pairs)}")


if __name__ == "__main__":
    main()
