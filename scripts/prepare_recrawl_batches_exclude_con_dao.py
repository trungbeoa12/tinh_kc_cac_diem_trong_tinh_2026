#!/usr/bin/env python3
"""Prepare three recrawl batches excluding PGD Con Dao.

This script only prepares inputs and shell runners. It does not run the
crawler and does not modify crawler logic.
"""

from __future__ import annotations

import argparse
import math
import stat
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


CON_DAO_CODE = "88033000"
CON_DAO_NAME = "PGD Con Dao"
BATCH_COUNT = 3

DEFAULT_COMPARE_DIR = config.PROJECT_ROOT / "outputs" / "compare_distance_3_periods"
DEFAULT_INPUT_FILE = DEFAULT_COMPARE_DIR / "pairs_need_recrawl.xlsx"
DEFAULT_BRANCHES_FILE = config.PROJECT_ROOT / "data_20260504_ver2" / "branches_20260504.xlsx"
DEFAULT_RUNNER_DIR = config.PROJECT_ROOT / "scripts" / "recrawl_batches"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--branches-file", type=Path, default=DEFAULT_BRANCHES_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_COMPARE_DIR)
    parser.add_argument("--runner-dir", type=Path, default=DEFAULT_RUNNER_DIR)
    parser.add_argument("--exclude-code", default=CON_DAO_CODE)
    return parser.parse_args()


def normalize_text(value: object) -> str:
    text = str(value or "").strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())


def normalize_code(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text.replace(".0", "").isdigit():
        text = text[:-2]
    return text


def find_code_columns(df: pd.DataFrame) -> tuple[str, str]:
    candidates = [
        ("ma_phong_ban_1", "ma_phong_ban_2"),
        ("Mã phòng ban 1", "Mã phòng ban 2"),
        ("ma_don_vi_1", "ma_don_vi_2"),
        ("Mã đơn vị 1", "Mã đơn vị 2"),
    ]
    for left, right in candidates:
        if left in df.columns and right in df.columns:
            return left, right
    raise ValueError(f"Không tìm thấy cặp cột mã đơn vị trong file. Columns: {list(df.columns)}")


def find_name_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    candidates = [
        ("ten_phong_ban_1", "ten_phong_ban_2"),
        ("Tên phòng ban 1", "Tên phòng ban 2"),
        ("ten_don_vi_1", "ten_don_vi_2"),
        ("Tên đơn vị 1", "Tên đơn vị 2"),
    ]
    for left, right in candidates:
        if left in df.columns and right in df.columns:
            return left, right
    return None, None


def verify_branches(branches_file: Path, exclude_code: str) -> list[str]:
    warnings: list[str] = []
    if not branches_file.exists():
        warnings.append(f"Không tìm thấy branches file để kiểm tra: {branches_file}")
        return warnings

    branches = pd.read_excel(branches_file)
    code_col = "Mã phòng ban" if "Mã phòng ban" in branches.columns else None
    name_col = "Tên phòng ban" if "Tên phòng ban" in branches.columns else None
    if not code_col or not name_col:
        warnings.append(f"Không tìm thấy cột Mã phòng ban/Tên phòng ban trong {branches_file.name}")
        return warnings

    code_mask = branches[code_col].map(normalize_code) == exclude_code
    name_mask = branches[name_col].map(normalize_text) == normalize_text(CON_DAO_NAME)
    code_rows = branches.loc[code_mask]
    name_rows = branches.loc[name_mask]

    if len(code_rows) == 0:
        warnings.append(f"Không tìm thấy mã {exclude_code} trong {branches_file.name}")
    else:
        unexpected = code_rows.loc[~code_rows[name_col].map(normalize_text).eq(normalize_text(CON_DAO_NAME))]
        if len(unexpected):
            warnings.append(
                f"Mã {exclude_code} có tên khác PGD Côn Đảo trong branches: "
                + "; ".join(map(str, unexpected[name_col].tolist()))
            )

    wrong_code = name_rows.loc[~name_rows[code_col].map(normalize_code).eq(exclude_code)]
    if len(wrong_code):
        warnings.append(
            "Có dòng tên PGD Côn Đảo nhưng mã khác 88033000 trong branches: "
            + "; ".join(map(str, wrong_code[code_col].tolist()))
        )
    return warnings


def find_mismatch_warnings(
    df: pd.DataFrame,
    code_cols: tuple[str, str],
    name_cols: tuple[str | None, str | None],
    exclude_code: str,
) -> list[str]:
    warnings: list[str] = []
    left_code_col, right_code_col = code_cols
    left_name_col, right_name_col = name_cols
    if not left_name_col or not right_name_col:
        warnings.append("Không tìm thấy đủ cột tên đơn vị trong pairs_need_recrawl để kiểm tra lệch mã/tên.")
        return warnings

    con_dao_name_norm = normalize_text(CON_DAO_NAME)
    checks = [
        (left_code_col, left_name_col, "đơn vị 1"),
        (right_code_col, right_name_col, "đơn vị 2"),
    ]
    for code_col, name_col, label in checks:
        code_is_con_dao = df[code_col].map(normalize_code) == exclude_code
        name_is_con_dao = df[name_col].map(normalize_text) == con_dao_name_norm

        code_name_mismatch = df.loc[code_is_con_dao & ~name_is_con_dao, [code_col, name_col]]
        if len(code_name_mismatch):
            sample = code_name_mismatch.head(5).to_dict("records")
            warnings.append(
                f"Có {len(code_name_mismatch)} dòng {label} có mã {exclude_code} nhưng tên không phải PGD Côn Đảo. "
                f"Ví dụ: {sample}"
            )

        name_code_mismatch = df.loc[name_is_con_dao & ~code_is_con_dao, [code_col, name_col]]
        if len(name_code_mismatch):
            sample = name_code_mismatch.head(5).to_dict("records")
            warnings.append(
                f"Có {len(name_code_mismatch)} dòng {label} tên PGD Côn Đảo nhưng mã không phải {exclude_code}. "
                f"Ví dụ: {sample}"
            )
    return warnings


def split_evenly(df: pd.DataFrame, batch_count: int) -> list[pd.DataFrame]:
    total = len(df)
    base_size = total // batch_count
    remainder = total % batch_count
    batches: list[pd.DataFrame] = []
    start = 0
    for idx in range(batch_count):
        size = base_size + (1 if idx < remainder else 0)
        end = start + size
        batches.append(df.iloc[start:end].copy().reset_index(drop=True))
        start = end
    return batches


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(config.PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_runner(runner_dir: Path, part_folder: Path, batch_num: int) -> Path:
    runner_dir.mkdir(parents=True, exist_ok=True)
    script_path = runner_dir / f"recrawl_batch_{batch_num:02d}.sh"
    output_dir = part_folder / f"output_part_{batch_num:02d}"
    content = f"""#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="{config.PROJECT_ROOT}"
cd "$PROJECT_ROOT"

PYTHON_BIN="${{PYTHON_BIN:-python3}}"
PART_FOLDER="{part_folder}"
PART_ID="{batch_num}"
BATCH_SIZE="${{BATCH_SIZE:-100}}"
SLEEP_TIME="${{SLEEP_TIME:-3}}"
WAIT_TIME="${{WAIT_TIME:-10}}"

echo "========== Recrawl batch {batch_num:02d} | $(date '+%Y-%m-%d %H:%M:%S') =========="
echo "Project root: $PROJECT_ROOT"
echo "Input part: $PART_FOLDER/df_part_{batch_num:02d}.pkl"
echo "Output dir: {output_dir}"
echo "BATCH_SIZE=$BATCH_SIZE SLEEP_TIME=$SLEEP_TIME WAIT_TIME=$WAIT_TIME"

mkdir -p "{output_dir}"

PART_FOLDER="$PART_FOLDER" \\
PART_ID="$PART_ID" \\
BATCH_SIZE="$BATCH_SIZE" \\
SLEEP_TIME="$SLEEP_TIME" \\
WAIT_TIME="$WAIT_TIME" \\
"$PYTHON_BIN" scripts/crawl_part.py

echo "========== Done recrawl batch {batch_num:02d} | $(date '+%Y-%m-%d %H:%M:%S') =========="
"""
    script_path.write_text(content, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script_path


def main() -> None:
    args = parse_args()
    input_file = args.input_file
    output_dir = args.output_dir
    part_folder = output_dir / "recrawl_part_inputs"

    if not input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy input file: {input_file}")

    df = pd.read_excel(input_file)
    code_cols = find_code_columns(df)
    name_cols = find_name_columns(df)
    left_code_col, right_code_col = code_cols

    initial_rows = len(df)
    con_dao_mask = (
        df[left_code_col].map(normalize_code).eq(args.exclude_code)
        | df[right_code_col].map(normalize_code).eq(args.exclude_code)
    )
    excluded = df.loc[con_dao_mask].copy()
    remaining = df.loc[~con_dao_mask].copy().reset_index(drop=True)

    warnings = [
        *verify_branches(args.branches_file, args.exclude_code),
        *find_mismatch_warnings(df, code_cols, name_cols, args.exclude_code),
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    part_folder.mkdir(parents=True, exist_ok=True)

    excluded_file = output_dir / "pairs_excluded_con_dao.xlsx"
    filtered_file = output_dir / "pairs_need_recrawl_exclude_con_dao.xlsx"
    remaining.to_excel(filtered_file, index=False, sheet_name="need_recrawl")
    excluded.to_excel(excluded_file, index=False, sheet_name="excluded_con_dao")

    batches = split_evenly(remaining, BATCH_COUNT)
    batch_rows: list[int] = []
    batch_files: list[Path] = []
    pkl_files: list[Path] = []
    for batch_num, batch_df in enumerate(batches, start=1):
        batch_file = output_dir / f"recrawl_batch_{batch_num:02d}.xlsx"
        pkl_file = part_folder / f"df_part_{batch_num:02d}.pkl"
        batch_df.to_excel(batch_file, index=False, sheet_name=f"batch_{batch_num:02d}")
        batch_df.to_pickle(pkl_file)
        batch_rows.append(len(batch_df))
        batch_files.append(batch_file)
        pkl_files.append(pkl_file)

    runners = [write_runner(args.runner_dir, part_folder, batch_num) for batch_num in range(1, BATCH_COUNT + 1)]

    summary_rows = [
        {"metric": "input_rows", "value": initial_rows},
        {"metric": "excluded_con_dao_rows", "value": len(excluded)},
        {"metric": "remaining_rows", "value": len(remaining)},
    ]
    for batch_num, rows in enumerate(batch_rows, start=1):
        summary_rows.append({"metric": f"recrawl_batch_{batch_num:02d}_rows", "value": rows})
    summary = pd.DataFrame(summary_rows)
    summary.to_excel(output_dir / "recrawl_batches_exclude_con_dao_summary.xlsx", index=False)

    print("Prepare recrawl batches excluding PGD Con Dao")
    print(f"Input file: {rel(input_file)}")
    print(f"Code columns: {left_code_col}, {right_code_col}")
    if name_cols[0] and name_cols[1]:
        print(f"Name columns: {name_cols[0]}, {name_cols[1]}")
    print(f"Initial rows: {initial_rows}")
    print(f"Excluded rows containing {args.exclude_code} - PGD Côn Đảo: {len(excluded)}")
    print(f"Remaining rows: {len(remaining)}")
    for batch_num, rows in enumerate(batch_rows, start=1):
        print(f"Rows recrawl_batch_{batch_num:02d}: {rows}")
    print(f"Filtered recrawl input: {rel(filtered_file)}")
    print(f"Excluded rows audit file: {rel(excluded_file)}")
    for batch_file in batch_files:
        print(f"Batch Excel: {rel(batch_file)}")
    for pkl_file in pkl_files:
        print(f"Crawler input pkl: {rel(pkl_file)}")
    for runner in runners:
        print(f"Shell script: {rel(runner)}")
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\nWarnings: none")

    print("\nSuggested commands:")
    for runner in runners:
        print(f"  bash {rel(runner)}")


if __name__ == "__main__":
    main()
