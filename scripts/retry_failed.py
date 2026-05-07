#!/usr/bin/env python
"""Extract failed rows from previous crawl and prepare for retry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Import config
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

PROJECT_ROOT = config.PROJECT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        type=str,
        default=config.DATA_VERSION,
        help=f"Data version (YYYYMMDD format). Default: {config.DATA_VERSION}",
    )
    
    # Build defaults from config
    paths = config.get_data_paths(config.DATA_VERSION)
    default_final = paths["final_file"]
    default_input = paths["crawl_pairs_file"]
    default_output = paths["input_folder"] / f"crawl_pairs_retry_{config.DATA_VERSION}.xlsx"
    
    parser.add_argument(
        "--final",
        type=Path,
        default=default_final,
        help="Path to final output file with crawl_status column",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        help="Path to original crawl_pairs input file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help="Path to write retry input file",
    )
    
    args = parser.parse_args()
    
    # If version changed, update paths
    if args.version != config.DATA_VERSION:
        paths = config.get_data_paths(args.version)
        if args.final == default_final:
            args.final = paths["final_file"]
        if args.input == default_input:
            args.input = paths["crawl_pairs_file"]
        if args.output == default_output:
            args.output = paths["input_folder"] / f"crawl_pairs_retry_{args.version}.xlsx"
    
    return args


def main() -> None:
    args = parse_args()
    final_file = args.final
    input_file = args.input
    output_file = args.output

    print(f"📖 Đọc file final: {final_file}")
    if not final_file.exists():
        raise FileNotFoundError(f"Không tìm thấy: {final_file}")

    df_final = pd.read_excel(final_file)

    if "crawl_status" not in df_final.columns:
        raise ValueError("File final không có cột 'crawl_status'")

    # Filter failed rows
    failed_mask = df_final["crawl_status"] != "ok"
    df_failed = df_final[failed_mask].copy()
    failed_count = len(df_failed)

    print(f"✅ Tìm thấy {failed_count} dòng thất bại")

    if failed_count == 0:
        print("🎉 Không có dòng nào thất bại. Không cần retry.")
        return

    # Read original input to get all columns
    print(f"📖 Đọc file input gốc: {input_file}")
    if not input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy: {input_file}")

    df_input = pd.read_excel(input_file)

    # Get global_index of failed rows
    if "global_index" not in df_failed.columns:
        raise ValueError("File final không có cột 'global_index'")

    failed_indices = df_failed["global_index"].tolist()

    # Extract corresponding rows from input
    df_retry = df_input[df_input.index.isin(failed_indices)].copy()

    # Reset distance column if exists
    if "Khoảng cách đường bộ" in df_retry.columns:
        df_retry["Khoảng cách đường bộ"] = None

    print(f"✍️  Ghi file retry: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_retry.to_excel(output_file, index=False)

    print(f"\n📊 Kết quả:")
    print(f"  - Dòng thất bại: {failed_count}")
    print(f"  - Dòng được chuẩn bị retry: {len(df_retry)}")
    print(f"\nBước tiếp theo:")
    print(f"  1. Chia thành part: python scripts/split_crawl_parts.py --source {output_file} --part-folder work/part_retry")
    print(f"  2. Chạy crawl: cd scripts && PART_FOLDER=../work/part_retry ./crawl_parts.sh 1 2 3 ...")
    print(f"  3. Merge kết quả: python scripts/merge_retry_results.py --original {final_file} --retry-part-folder work/part_retry")


if __name__ == "__main__":
    main()
