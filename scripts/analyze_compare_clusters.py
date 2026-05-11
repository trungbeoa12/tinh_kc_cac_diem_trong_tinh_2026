#!/usr/bin/env python
"""Analyze clustering of suspicious compare results.

This script reads compare_full_results.csv and checks whether HIGH,
SUSPECT_CHANGED, and NEW_MISSING rows are concentrated by PART_ID, province,
machine_id, or crawl timestamp buckets. It does not modify source files and
does not crawl Google Maps.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


DEFAULT_COMPARE_FILE = (
    config.PROJECT_ROOT
    / "debug_outputs"
    / "compare_20260504_vs_20260312"
    / "compare_full_results.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-file", type=Path, default=DEFAULT_COMPARE_FILE)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def read_compare_file(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Compare file not found: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "compare_status" not in df.columns:
        raise ValueError("Missing required column: compare_status")
    if "recrawl_priority" not in df.columns:
        raise ValueError("Missing required column: recrawl_priority")
    if "distance_change_pct" in df.columns:
        df["distance_change_pct"] = pd.to_numeric(df["distance_change_pct"], errors="coerce")
    else:
        df["distance_change_pct"] = pd.NA
    return df


def status_count(series: pd.Series, status: str) -> int:
    return int((series == status).sum())


def priority_count(series: pd.Series, priority: str) -> int:
    return int((series == priority).sum())


def aggregate_cluster(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for group_value, group in df.groupby(group_col, dropna=False):
        total_rows = len(group)
        high_count = priority_count(group["recrawl_priority"], "HIGH")
        row = {
            group_col: group_value,
            "total_rows": total_rows,
            "consistent_count": status_count(group["compare_status"], "CONSISTENT_WITH_OLD"),
            "watch_count": status_count(group["compare_status"], "WATCH_CHANGED"),
            "suspect_changed_count": status_count(group["compare_status"], "SUSPECT_CHANGED"),
            "new_missing_count": status_count(group["compare_status"], "NEW_MISSING"),
            "high_count": high_count,
            "medium_count": priority_count(group["recrawl_priority"], "MEDIUM"),
            "high_rate": round(high_count / total_rows, 4) if total_rows else 0,
            "avg_distance_change_pct": round(group["distance_change_pct"].mean(skipna=True), 4),
            "median_distance_change_pct": round(group["distance_change_pct"].median(skipna=True), 4),
            "max_distance_change_pct": round(group["distance_change_pct"].max(skipna=True), 4),
        }
        rows.append(row)

    result = pd.DataFrame(rows)
    return result.sort_values(["high_count", "high_rate"], ascending=[False, False])


def top_bad_parts(cluster_by_part: pd.DataFrame) -> pd.DataFrame:
    high_count_top = cluster_by_part.sort_values("high_count", ascending=False).head(50)
    high_rate_top = cluster_by_part.sort_values("high_rate", ascending=False).head(50)
    avg_change_top = cluster_by_part.sort_values("avg_distance_change_pct", ascending=False).head(50)
    combined = pd.concat([high_count_top, high_rate_top, avg_change_top], ignore_index=True)
    return combined.drop_duplicates("PART_ID").sort_values(
        ["high_count", "high_rate", "avg_distance_change_pct"],
        ascending=[False, False, False],
    )


def build_bad_rows(df: pd.DataFrame) -> pd.DataFrame:
    bad_mask = (
        df["recrawl_priority"].eq("HIGH")
        | df["compare_status"].isin(["SUSPECT_CHANGED", "NEW_MISSING"])
    )
    sort_cols = [col for col in ["recrawl_priority", "distance_abs_diff_km", "distance_change_pct"] if col in df.columns]
    ascending = [True, False, False][: len(sort_cols)]
    result = df.loc[bad_mask].copy()
    if sort_cols:
        result = result.sort_values(sort_cols, ascending=ascending, na_position="last")
    return result.head(500)


def add_time_buckets(df: pd.DataFrame) -> pd.DataFrame:
    if "crawl_timestamp" not in df.columns:
        return df
    result = df.copy()
    timestamps = pd.to_datetime(result["crawl_timestamp"], errors="coerce")
    result["crawl_date"] = timestamps.dt.date.astype("string")
    result["crawl_hour"] = timestamps.dt.strftime("%Y-%m-%d %H:00")
    return result


def concentration_note(cluster: pd.DataFrame, group_col: str) -> str:
    total_high = int(cluster["high_count"].sum()) if "high_count" in cluster.columns else 0
    if total_high == 0 or cluster.empty:
        return f"{group_col}: không có HIGH để đánh giá tập trung."

    top1 = cluster.sort_values("high_count", ascending=False).iloc[0]
    top5_high = int(cluster.sort_values("high_count", ascending=False).head(5)["high_count"].sum())
    top1_share = top1["high_count"] / total_high
    top5_share = top5_high / total_high

    if top1_share >= 0.30 or top5_share >= 0.70:
        pattern = "lỗi có dấu hiệu tập trung"
    elif top1_share <= 0.10 and top5_share <= 0.35:
        pattern = "lỗi khá rải đều"
    else:
        pattern = "lỗi phân bố vừa rải vừa có cụm nổi bật"

    return (
        f"{group_col}: {pattern}. Top 1 chiếm {top1_share:.1%} HIGH, "
        f"top 5 chiếm {top5_share:.1%} HIGH."
    )


def print_top(title: str, df: pd.DataFrame, cols: list[str]) -> None:
    print(f"\n{title}")
    if df.empty:
        print("  Không có dữ liệu.")
        return
    print(df[cols].head(20).to_string(index=False))


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or args.compare_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    df = add_time_buckets(read_compare_file(args.compare_file))

    if "PART_ID" not in df.columns:
        raise ValueError("Missing required column for part analysis: PART_ID")

    cluster_by_part = aggregate_cluster(df, "PART_ID")
    cluster_by_part.to_csv(output_dir / "cluster_by_part.csv", index=False, encoding="utf-8-sig")

    bad_parts = top_bad_parts(cluster_by_part)
    bad_parts.to_csv(output_dir / "top_bad_parts.csv", index=False, encoding="utf-8-sig")

    top_bad_rows = build_bad_rows(df)
    top_bad_rows.to_csv(output_dir / "top_500_bad_rows.csv", index=False, encoding="utf-8-sig")

    cluster_by_province = None
    if "tinh_thanh" in df.columns:
        cluster_by_province = aggregate_cluster(df, "tinh_thanh")
        cluster_by_province.to_csv(output_dir / "cluster_by_province.csv", index=False, encoding="utf-8-sig")

    cluster_by_machine = None
    if "machine_id" in df.columns:
        cluster_by_machine = aggregate_cluster(df, "machine_id")
        cluster_by_machine.to_csv(output_dir / "cluster_by_machine.csv", index=False, encoding="utf-8-sig")

    if "crawl_hour" in df.columns:
        aggregate_cluster(df.dropna(subset=["crawl_hour"]), "crawl_hour").to_csv(
            output_dir / "cluster_by_crawl_hour.csv", index=False, encoding="utf-8-sig"
        )
    if "crawl_date" in df.columns:
        aggregate_cluster(df.dropna(subset=["crawl_date"]), "crawl_date").to_csv(
            output_dir / "cluster_by_crawl_date.csv", index=False, encoding="utf-8-sig"
        )

    part_cols = [
        "PART_ID",
        "total_rows",
        "high_count",
        "high_rate",
        "suspect_changed_count",
        "new_missing_count",
        "avg_distance_change_pct",
        "max_distance_change_pct",
    ]
    print(f"Compare file: {args.compare_file}")
    print(f"Output dir: {output_dir}")
    print_top(
        "Top 20 PART_ID by high_count",
        cluster_by_part.sort_values("high_count", ascending=False),
        part_cols,
    )
    print_top(
        "Top 20 PART_ID by high_rate",
        cluster_by_part.sort_values(["high_rate", "high_count"], ascending=[False, False]),
        part_cols,
    )

    notes = [concentration_note(cluster_by_part, "PART_ID")]
    if cluster_by_province is not None:
        province_cols = [
            "tinh_thanh",
            "total_rows",
            "high_count",
            "high_rate",
            "suspect_changed_count",
            "new_missing_count",
            "avg_distance_change_pct",
            "max_distance_change_pct",
        ]
        print_top(
            "Top 20 tinh_thanh by high_count",
            cluster_by_province.sort_values("high_count", ascending=False),
            province_cols,
        )
        notes.append(concentration_note(cluster_by_province, "tinh_thanh"))

    if cluster_by_machine is not None:
        notes.append(concentration_note(cluster_by_machine, "machine_id"))

    print("\nNhận xét")
    for note in notes:
        print(f"- {note}")


if __name__ == "__main__":
    main()
