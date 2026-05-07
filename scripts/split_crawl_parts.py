import argparse
import sys
from math import ceil
from pathlib import Path

import pandas as pd

# Import config
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

PROJECT_ROOT = config.PROJECT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split crawl input into pickle parts.")
    parser.add_argument(
        "--version",
        type=str,
        default=config.DATA_VERSION,
        help=f"Data version (YYYYMMDD format). Default: {config.DATA_VERSION}",
    )
    
    # Build defaults from config
    paths = config.get_data_paths(config.DATA_VERSION)
    default_source = paths["crawl_pairs_file"]
    default_part_folder = config.PART_FOLDER
    default_rows_per_part = 100
    
    parser.add_argument("--source", type=Path, default=default_source)
    parser.add_argument("--part-folder", type=Path, default=default_part_folder)
    parser.add_argument("--rows-per-part", type=int, default=default_rows_per_part)
    
    args = parser.parse_args()
    
    # If version changed, update source path
    if args.version != config.DATA_VERSION:
        paths = config.get_data_paths(args.version)
        if args.source == default_source:
            args.source = paths["crawl_pairs_file"]
    
    return args


def main() -> None:
    args = parse_args()
    source_file = args.source
    part_folder = args.part_folder
    rows_per_part = args.rows_per_part

    print("Đọc file nguồn:", source_file)
    if not source_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {source_file}")

    df = pd.read_excel(source_file)
    print("Tổng số dòng:", len(df))
    print("Các cột:", list(df.columns))

    # Nếu chưa có cột 'Khoảng cách đường bộ' thì thêm để khớp script crawl
    if config.DISTANCE_COL not in df.columns:
        df[config.DISTANCE_COL] = None

    part_folder.mkdir(parents=True, exist_ok=True)

    num_parts = ceil(len(df) / rows_per_part)
    print("Số part sẽ tạo:", num_parts)

    for part_idx in range(num_parts):
        start = part_idx * rows_per_part
        end = min((part_idx + 1) * rows_per_part, len(df))
        df_part = df.iloc[start:end].copy()

        part_id = part_idx + 1
        out_path = part_folder / f"df_part_{part_id:02d}.pkl"
        df_part.to_pickle(out_path)
        print(f"Đã lưu part {part_id:02d}: dòng {start}–{end-1} -> {out_path}")

    print("Hoàn tất chia part.")


if __name__ == "__main__":
    main()
