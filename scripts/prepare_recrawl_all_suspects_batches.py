#!/usr/bin/env python
"""Prepare HIGH and MEDIUM suspect rows for recrawl batches.

This script only prepares input CSVs and shell runners. It does not open
Google Maps or run the crawler.
"""

from __future__ import annotations

import argparse
import math
import os
import stat
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


DEFAULT_COMPARE_DIR = config.PROJECT_ROOT / "debug_outputs/compare_20260504_vs_20260312"
DEFAULT_OUTPUT_DIR = config.PROJECT_ROOT / "debug_outputs/recrawl_all_suspects_20260504_vs_20260312"
BATCH_COUNT = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--high-file",
        type=Path,
        default=DEFAULT_COMPARE_DIR / "recrawl_high_priority.csv",
        help="HIGH priority CSV from compare output.",
    )
    parser.add_argument(
        "--medium-file",
        type=Path,
        default=DEFAULT_COMPARE_DIR / "recrawl_medium_priority.csv",
        help="MEDIUM priority CSV from compare output.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for combined input, batch CSVs, runners, and summary.",
    )
    return parser.parse_args()


def read_priority_file(path: Path, recrawl_group: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file input: {path}")

    df = pd.read_csv(path, encoding="utf-8-sig")
    df["recrawl_group"] = recrawl_group
    return df


def build_pair_key(df: pd.DataFrame) -> pd.Series:
    required = ["ma_phong_ban_1", "ma_phong_ban_2"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột để tạo pair_key: {', '.join(missing)}")

    return (
        df["ma_phong_ban_1"].astype(str).str.strip()
        + "__"
        + df["ma_phong_ban_2"].astype(str).str.strip()
    )


def dedupe_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    work = df.copy()
    work["pair_key"] = build_pair_key(work)
    work["_priority_rank"] = work["recrawl_group"].map({"HIGH": 0, "MEDIUM": 1}).fillna(9)

    if "distance_change_pct" in work.columns:
        work["_distance_change_pct_num"] = pd.to_numeric(work["distance_change_pct"], errors="coerce").fillna(-math.inf)
    else:
        work["_distance_change_pct_num"] = -math.inf

    before = len(work)
    work = work.sort_values(
        by=["_priority_rank", "_distance_change_pct_num"],
        ascending=[True, False],
        kind="mergesort",
    )
    work = work.drop_duplicates(subset=["pair_key"], keep="first")
    removed = before - len(work)
    work = work.drop(columns=["_priority_rank", "_distance_change_pct_num"])
    return work.reset_index(drop=True), removed


def sort_rows_for_recrawl(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "distance_change_pct" in work.columns:
        work["_distance_change_pct_num"] = pd.to_numeric(work["distance_change_pct"], errors="coerce").fillna(-math.inf)
    else:
        work["_distance_change_pct_num"] = -math.inf

    if "tinh_thanh" not in work.columns:
        return work.sort_values("_distance_change_pct_num", ascending=False, kind="mergesort").drop(
            columns=["_distance_change_pct_num"]
        )

    province_order = (
        work["tinh_thanh"]
        .fillna("")
        .astype(str)
        .value_counts()
        .sort_values(ascending=False)
        .index.tolist()
    )
    buckets = {
        province: province_df.sort_values("_distance_change_pct_num", ascending=False, kind="mergesort")
        for province, province_df in work.groupby(work["tinh_thanh"].fillna("").astype(str), sort=False)
    }

    ordered_chunks: list[pd.DataFrame] = []
    while buckets:
        for province in list(province_order):
            province_df = buckets.get(province)
            if province_df is None:
                continue
            ordered_chunks.append(province_df.head(1))
            province_df = province_df.iloc[1:]
            if province_df.empty:
                del buckets[province]
                province_order.remove(province)
            else:
                buckets[province] = province_df

    return pd.concat(ordered_chunks, ignore_index=True).drop(columns=["_distance_change_pct_num"])


def assign_batches(df: pd.DataFrame) -> pd.DataFrame:
    ordered = sort_rows_for_recrawl(df)
    total_rows = len(ordered)
    base_size = total_rows // BATCH_COUNT
    remainder = total_rows % BATCH_COUNT
    target_sizes = {
        batch_idx: base_size + (1 if batch_idx < remainder else 0)
        for batch_idx in range(BATCH_COUNT)
    }
    current_sizes = {batch_idx: 0 for batch_idx in range(BATCH_COUNT)}
    assignments: dict[int, str] = {}

    if "tinh_thanh" in ordered.columns:
        province_counts = ordered["tinh_thanh"].fillna("").astype(str).value_counts()
        provinces = province_counts.sort_values(ascending=False).index.tolist()
        province_start_offsets = {
            province: province_idx % BATCH_COUNT
            for province_idx, province in enumerate(provinces)
        }
        grouped = ordered.groupby(ordered["tinh_thanh"].fillna("").astype(str), sort=False)

        for province in provinces:
            province_df = grouped.get_group(province)
            start_offset = province_start_offsets[province]
            for offset, row_index in enumerate(province_df.index):
                preferred = [(start_offset + offset + step) % BATCH_COUNT for step in range(BATCH_COUNT)]
                available = [
                    batch_idx
                    for batch_idx in preferred
                    if current_sizes[batch_idx] < target_sizes[batch_idx]
                ]
                if not available:
                    available = list(range(BATCH_COUNT))
                batch_idx = min(available, key=lambda item: (current_sizes[item], item))
                assignments[row_index] = f"batch_{batch_idx + 1:02d}"
                current_sizes[batch_idx] += 1
    else:
        for offset, row_index in enumerate(ordered.index):
            preferred = [((offset + step) % BATCH_COUNT) for step in range(BATCH_COUNT)]
            available = [
                batch_idx
                for batch_idx in preferred
                if current_sizes[batch_idx] < target_sizes[batch_idx]
            ]
            batch_idx = available[0] if available else min(current_sizes, key=current_sizes.get)
            assignments[row_index] = f"batch_{batch_idx + 1:02d}"
            current_sizes[batch_idx] += 1

    ordered["recrawl_batch"] = ordered.index.map(assignments)
    return ordered.reset_index(drop=True)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(config.PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_runner(output_dir: Path, batch_num: int) -> Path:
    batch_label = f"batch_{batch_num:02d}"
    batch_file = output_dir / f"recrawl_{batch_label}.csv"
    batch_output_dir = output_dir / f"output_{batch_label}"
    log_file = output_dir / "logs" / f"recrawl_{batch_label}.log"
    script_path = output_dir / f"run_recrawl_{batch_label}.sh"

    content = f"""#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

mkdir -p "{rel(output_dir / "logs")}"
mkdir -p "{rel(batch_output_dir)}"

echo "Start time: $(date)"
echo "Input file: {rel(batch_file)}"
echo "Output dir: {rel(batch_output_dir)}"

python scripts/recrawl_high_priority.py \\
  --input-file "{rel(batch_file)}" \\
  --output-dir "{rel(batch_output_dir)}" \\
  --machine-id "BATCH_{batch_num:02d}" \\
  2>&1 | tee "{rel(log_file)}"

echo "End time: $(date)"
"""
    script_path.write_text(content, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script_path


def write_run_all(output_dir: Path) -> Path:
    script_path = output_dir / "run_all_recrawl_batches.sh"
    content = """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

bash run_recrawl_batch_01.sh
bash run_recrawl_batch_02.sh
bash run_recrawl_batch_03.sh

# Nếu muốn chạy song song, có thể tự chạy 3 lệnh dưới đây ở 3 terminal riêng:
# bash run_recrawl_batch_01.sh
# bash run_recrawl_batch_02.sh
# bash run_recrawl_batch_03.sh
"""
    script_path.write_text(content, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script_path


def build_summary(batch_frames: dict[str, pd.DataFrame], output_dir: Path, scripts: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for batch_num in range(1, BATCH_COUNT + 1):
        batch_label = f"batch_{batch_num:02d}"
        batch_file = output_dir / f"recrawl_{batch_label}.csv"
        df = batch_frames[batch_label]
        province_counts = (
            df["tinh_thanh"].fillna("").astype(str).value_counts()
            if "tinh_thanh" in df.columns and not df.empty
            else pd.Series(dtype="int64")
        )
        top_province = province_counts.index[0] if not province_counts.empty else ""
        top_province_rows = int(province_counts.iloc[0]) if not province_counts.empty else 0
        rows.append(
            {
                "batch_file": rel(batch_file),
                "rows": len(df),
                "high_rows": int((df["recrawl_group"] == "HIGH").sum()),
                "medium_rows": int((df["recrawl_group"] == "MEDIUM").sum()),
                "top_1_tinh_thanh": top_province,
                "top_1_tinh_thanh_rows": top_province_rows,
                "output_dir": rel(output_dir / f"output_{batch_label}"),
                "shell_script": rel(scripts[batch_label]),
                "log_file": rel(output_dir / "logs" / f"recrawl_{batch_label}.log"),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    high_df = read_priority_file(args.high_file, "HIGH")
    medium_df = read_priority_file(args.medium_file, "MEDIUM")
    combined_before = pd.concat([high_df, medium_df], ignore_index=True)
    deduped, duplicate_removed = dedupe_rows(combined_before)
    prepared = assign_batches(deduped)

    all_file = output_dir / "recrawl_all_suspects.csv"
    prepared.to_csv(all_file, index=False, encoding="utf-8-sig")

    batch_frames: dict[str, pd.DataFrame] = {}
    batch_files: dict[str, Path] = {}
    for batch_num in range(1, BATCH_COUNT + 1):
        batch_label = f"batch_{batch_num:02d}"
        batch_df = prepared[prepared["recrawl_batch"] == batch_label].copy()
        batch_file = output_dir / f"recrawl_{batch_label}.csv"
        batch_df.to_csv(batch_file, index=False, encoding="utf-8-sig")
        batch_frames[batch_label] = batch_df
        batch_files[batch_label] = batch_file

    scripts = {f"batch_{num:02d}": write_runner(output_dir, num) for num in range(1, BATCH_COUNT + 1)}
    run_all_script = write_run_all(output_dir)

    summary = build_summary(batch_frames, output_dir, scripts)
    summary_file = output_dir / "recrawl_batch_summary.csv"
    summary.to_csv(summary_file, index=False, encoding="utf-8-sig")

    print("Prepare recrawl all suspects batches")
    print(f"  HIGH input rows: {len(high_df)}")
    print(f"  MEDIUM input rows: {len(medium_df)}")
    print(f"  Total before dedupe: {len(combined_before)}")
    print(f"  Duplicate rows removed: {duplicate_removed}")
    print(f"  Total after dedupe: {len(prepared)}")
    for batch_num in range(1, BATCH_COUNT + 1):
        batch_label = f"batch_{batch_num:02d}"
        print(f"  Rows {batch_label}: {len(batch_frames[batch_label])}")
    print(f"  Combined file: {rel(all_file)}")
    for batch_num in range(1, BATCH_COUNT + 1):
        batch_label = f"batch_{batch_num:02d}"
        print(f"  Batch file {batch_label}: {rel(batch_files[batch_label])}")
    for batch_num in range(1, BATCH_COUNT + 1):
        batch_label = f"batch_{batch_num:02d}"
        print(f"  Shell script {batch_label}: {rel(scripts[batch_label])}")
    print(f"  Run-all script: {rel(run_all_script)}")
    print(f"  Summary file: {rel(summary_file)}")
    print("\nSuggested commands:")
    for batch_num in range(1, BATCH_COUNT + 1):
        batch_label = f"batch_{batch_num:02d}"
        print(f"  bash {rel(scripts[batch_label])}")
    print(f"  bash {rel(run_all_script)}")


if __name__ == "__main__":
    main()
