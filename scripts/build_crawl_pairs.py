#!/usr/bin/env python
"""Generate Google Maps crawl input from a branch/PGD coordinate Excel file."""

from __future__ import annotations

import argparse
import sys
from itertools import combinations
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd

# Import config
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Use config for defaults, can override with --version argument
PROJECT_ROOT = config.PROJECT_ROOT


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Return great-circle distance in kilometers between two lon/lat points."""
    earth_radius_km = 6371.0088
    lon1_rad, lat1_rad, lon2_rad, lat2_rad = map(
        radians, [lon1, lat1, lon2, lat2]
    )
    delta_lon = lon2_rad - lon1_rad
    delta_lat = lat2_rad - lat1_rad
    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * atan2(sqrt(a), sqrt(1 - a))


def load_points(input_path: Path, sheet_name: str | int = 0) -> pd.DataFrame:
    df = pd.read_excel(input_path, sheet_name=sheet_name)
    missing = [column for column in config.COLUMN_MAP if column not in df.columns]
    if missing:
        raise ValueError(f"Input file is missing required columns: {missing}")

    points = df[list(config.COLUMN_MAP)].rename(columns=config.COLUMN_MAP).copy()
    points = points.dropna(subset=list(config.COLUMN_MAP.values()))
    points["ma_phong_ban"] = points["ma_phong_ban"].astype("int64")
    points["kinh_do"] = points["kinh_do"].astype(float)
    points["vi_do"] = points["vi_do"].astype(float)
    points["ten_phong_ban"] = points["ten_phong_ban"].astype(str).str.strip()
    points["tinh_thanh"] = points["tinh_thanh"].astype(str).str.strip()

    duplicate_count = points["ma_phong_ban"].duplicated().sum()
    if duplicate_count:
        raise ValueError(f"Found duplicate ma_phong_ban values: {duplicate_count}")

    return points


def build_same_province_pairs(points: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for province, group in points.groupby("tinh_thanh", sort=True):
        records = group.sort_values("ma_phong_ban").to_dict("records")
        for first, second in combinations(records, 2):
            rows.append(
                {
                    "ma_phong_ban_1": first["ma_phong_ban"],
                    "ten_phong_ban_1": first["ten_phong_ban"],
                    "kinh_do_1": first["kinh_do"],
                    "vi_do_1": first["vi_do"],
                    "ma_phong_ban_2": second["ma_phong_ban"],
                    "ten_phong_ban_2": second["ten_phong_ban"],
                    "kinh_do_2": second["kinh_do"],
                    "vi_do_2": second["vi_do"],
                    "khoang_cach_chim_bay": haversine_km(
                        first["kinh_do"],
                        first["vi_do"],
                        second["kinh_do"],
                        second["vi_do"],
                    ),
                    "tinh_thanh": province,
                }
            )

    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create crawl input pairs from data_YYYYMMDD.xlsx."
    )
    parser.add_argument(
        "--version",
        type=str,
        default=config.DATA_VERSION,
        help=f"Data version (YYYYMMDD format). Default: {config.DATA_VERSION}",
    )
    
    # Allow override, but use config defaults
    paths = config.get_data_paths(config.DATA_VERSION)
    default_input = paths["branches_file"]
    default_output = paths["crawl_pairs_file"]
    default_sample = config.WORK_FOLDER / f"crawl_pairs_{config.DATA_VERSION}_sample.csv"
    
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--sample", type=Path, default=default_sample)
    parser.add_argument("--sheet", default=0)
    parser.add_argument("--sample-rows", type=int, default=20)
    
    args = parser.parse_args()
    
    # If version changed, update paths accordingly
    if args.version != config.DATA_VERSION:
        paths = config.get_data_paths(args.version)
        if args.input == default_input:
            args.input = paths["branches_file"]
        if args.output == default_output:
            args.output = paths["crawl_pairs_file"]
    
    return args


def main() -> None:
    args = parse_args()
    points = load_points(args.input, sheet_name=args.sheet)
    result = build_same_province_pairs(points)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_excel(args.output, index=False)

    if args.sample:
        args.sample.parent.mkdir(parents=True, exist_ok=True)
        result.head(args.sample_rows).to_csv(args.sample, index=False)

    print(f"Input rows: {len(points)}")
    print(f"Output rows: {len(result)}")
    print(f"Output file: {args.output}")
    if args.sample:
        print(f"Sample file: {args.sample}")


if __name__ == "__main__":
    main()
