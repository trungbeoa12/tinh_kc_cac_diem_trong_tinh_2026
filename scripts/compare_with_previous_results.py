#!/usr/bin/env python
"""Compare a new Google Maps crawl result file with a previous result file.

The comparison is based only on pair keys built from branch codes and rounded
coordinates. It does not use row order, PART_ID, row_in_part, or any index-like
columns for matching.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


CANONICAL_COLUMNS = [
    "ma_phong_ban_1",
    "ten_phong_ban_1",
    "kinh_do_1",
    "vi_do_1",
    "ma_phong_ban_2",
    "ten_phong_ban_2",
    "kinh_do_2",
    "vi_do_2",
    "tinh_thanh",
    "khoang_cach_chim_bay",
    "Khoảng cách đường bộ km",
    "Khoảng cách đường bộ",
    "thời gian",
]

COLUMN_ALIASES = {
    "ma_phong_ban_1": [
        "ma_phong_ban_1",
        "ma phong ban 1",
        "ma phong ban dau",
        "ma phong ban di",
        "ma phong ban origin",
    ],
    "ten_phong_ban_1": [
        "ten_phong_ban_1",
        "ten phong ban 1",
        "ten phong ban dau",
        "ten phong ban di",
        "ten phong ban origin",
    ],
    "kinh_do_1": ["kinh_do_1", "kinh do 1", "longitude 1", "lon 1", "lng 1"],
    "vi_do_1": ["vi_do_1", "vi do 1", "latitude 1", "lat 1"],
    "ma_phong_ban_2": [
        "ma_phong_ban_2",
        "ma phong ban 2",
        "ma phong ban cuoi",
        "ma phong ban den",
        "ma phong ban destination",
    ],
    "ten_phong_ban_2": [
        "ten_phong_ban_2",
        "ten phong ban 2",
        "ten phong ban cuoi",
        "ten phong ban den",
        "ten phong ban destination",
    ],
    "kinh_do_2": ["kinh_do_2", "kinh do 2", "longitude 2", "lon 2", "lng 2"],
    "vi_do_2": ["vi_do_2", "vi do 2", "latitude 2", "lat 2"],
    "tinh_thanh": ["tinh_thanh", "tinh thanh", "tinh", "province"],
    "khoang_cach_chim_bay": [
        "khoang_cach_chim_bay",
        "khoang cach chim bay",
        "khoang cach duong chim bay",
        "air distance",
        "air_distance_km",
    ],
    "Khoảng cách đường bộ km": [
        "khoang cach duong bo km",
        "khoang_cach_duong_bo_km",
        "road distance km",
        "distance km",
        "distance_km",
        "parsed_distance_km",
    ],
    "Khoảng cách đường bộ": [
        "khoang cach duong bo",
        "khoang_cach_duong_bo",
        "road distance",
        "distance",
    ],
    "thời gian": ["thoi gian", "thời gian", "duration", "time", "travel time"],
}

MATCH_METHODS = [
    "directed_pair_key_by_code",
    "undirected_pair_key_by_code",
    "directed_pair_key_by_coord",
    "undirected_pair_key_by_coord",
]

COMPARE_STATUS_ORDER = [
    "NEW_MISSING",
    "NO_OLD_BASELINE",
    "OLD_MISSING",
    "NEW_SUSPECT_OLD_OK",
    "SUSPECT_CHANGED",
    "BOTH_SUSPECT",
    "WATCH_CHANGED",
    "NEW_OK_OLD_SUSPECT",
    "CONSISTENT_WITH_OLD",
]

HIGH_PRIORITY = {"NEW_SUSPECT_OLD_OK", "SUSPECT_CHANGED", "NEW_MISSING"}
MEDIUM_PRIORITY = {"BOTH_SUSPECT", "WATCH_CHANGED", "NO_OLD_BASELINE", "OLD_MISSING"}
LOW_PRIORITY = {"CONSISTENT_WITH_OLD", "NEW_OK_OLD_SUSPECT"}

DISTANCE_WITH_UNIT_RE = re.compile(r"(?P<num>\d+(?:[,.]\d+)?)\s*(?P<unit>km|m)\b", re.I)
DURATION_RE = re.compile(
    r"(?:(?:\d+\s*(?:hr|hour|hours|h|gio|giờ))\s*)?\d+\s*(?:min|mins|minute|minutes|phut|phút)\b|"
    r"\d+\s*(?:hr|hour|hours|h|gio|giờ)\b",
    re.I,
)
NUMBER_ONLY_RE = re.compile(r"^\s*\d+(?:[,.]\d+)?\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-file", type=Path, required=True)
    parser.add_argument("--old-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=config.PROJECT_ROOT / "debug_outputs")
    return parser.parse_args()


def normalize_name(value: object) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        lookup[normalize_name(canonical)] = canonical
        for alias in aliases:
            lookup[normalize_name(alias)] = canonical
    return lookup


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="utf-8")
    raise ValueError(f"Unsupported file type: {path}")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    alias_lookup = build_alias_lookup()
    renamed: dict[str, str] = {}
    used: set[str] = set()

    for column in df.columns:
        canonical = alias_lookup.get(normalize_name(column))
        if canonical and canonical not in used:
            renamed[column] = canonical
            used.add(canonical)

    result = df.rename(columns=renamed).copy()
    for column in CANONICAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA
    return result


def is_missing(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def normalize_code(value: object) -> str | None:
    if is_missing(value):
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]
    return text


def coord_token(lat: object, lon: object) -> str | None:
    try:
        if pd.isna(lat) or pd.isna(lon):
            return None
        return f"{float(lat):.5f},{float(lon):.5f}"
    except (TypeError, ValueError):
        return None


def make_keys(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    code1 = result["ma_phong_ban_1"].apply(normalize_code)
    code2 = result["ma_phong_ban_2"].apply(normalize_code)
    coord1 = result.apply(lambda row: coord_token(row["vi_do_1"], row["kinh_do_1"]), axis=1)
    coord2 = result.apply(lambda row: coord_token(row["vi_do_2"], row["kinh_do_2"]), axis=1)

    result["directed_pair_key_by_code"] = [
        f"{first}__{second}" if first and second else pd.NA for first, second in zip(code1, code2)
    ]
    result["undirected_pair_key_by_code"] = [
        "__".join(sorted([first, second])) if first and second else pd.NA
        for first, second in zip(code1, code2)
    ]
    result["directed_pair_key_by_coord"] = [
        f"{first}__{second}" if first and second else pd.NA
        for first, second in zip(coord1, coord2)
    ]
    result["undirected_pair_key_by_coord"] = [
        "__".join(sorted([first, second])) if first and second else pd.NA
        for first, second in zip(coord1, coord2)
    ]
    return result


def parse_number(value: object) -> float | None:
    if is_missing(value):
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip()
    if not NUMBER_ONLY_RE.fullmatch(text):
        return None
    return float(text.replace(",", "."))


def parse_distance_km(row: pd.Series) -> float | None:
    explicit_km = parse_number(row.get("Khoảng cách đường bộ km"))
    if explicit_km is not None:
        return round(explicit_km, 2)

    raw = row.get("Khoảng cách đường bộ")
    numeric_raw = parse_number(raw)
    if numeric_raw is not None:
        return round(numeric_raw, 2)

    if is_missing(raw):
        return None
    text = str(raw)
    matches = list(DISTANCE_WITH_UNIT_RE.finditer(text))
    if not matches:
        return None

    match = matches[-1]
    number = float(match.group("num").replace(",", "."))
    unit = match.group("unit").lower()
    return round(number if unit == "km" else number / 1000, 2)


def parse_duration(row: pd.Series) -> str | None:
    duration = row.get("thời gian")
    if not is_missing(duration):
        return str(duration).strip()
    raw = row.get("Khoảng cách đường bộ")
    if is_missing(raw):
        return None
    match = DURATION_RE.search(str(raw))
    return match.group(0) if match else None


def ratio_to_air(distance_km: float | None, air_distance_km: object) -> float | None:
    air = parse_number(air_distance_km)
    if distance_km is None or air is None or air <= 0:
        return None
    return round(distance_km / air, 4)


def build_old_indexes(old_df: pd.DataFrame) -> dict[str, dict[str, int]]:
    indexes: dict[str, dict[str, int]] = {method: {} for method in MATCH_METHODS}
    for idx, row in old_df.iterrows():
        for method in MATCH_METHODS:
            key = row.get(method)
            if is_missing(key):
                continue
            indexes[method].setdefault(str(key), idx)
    return indexes


def find_old_match(row: pd.Series, old_indexes: dict[str, dict[str, int]]) -> tuple[str, int | None]:
    for method in MATCH_METHODS:
        key = row.get(method)
        if is_missing(key):
            continue
        old_idx = old_indexes[method].get(str(key))
        if old_idx is not None:
            return method, old_idx
    return "NO_OLD_BASELINE", None


def choose_compare_status(
    matched_by: str,
    new_distance_km: float | None,
    old_distance_km: float | None,
    new_ratio: float | None,
    old_ratio: float | None,
    distance_change_pct: float | None,
) -> str:
    candidates: set[str] = set()

    if new_distance_km is None:
        candidates.add("NEW_MISSING")
    if matched_by == "NO_OLD_BASELINE":
        candidates.add("NO_OLD_BASELINE")
    if matched_by != "NO_OLD_BASELINE" and old_distance_km is None:
        candidates.add("OLD_MISSING")

    if new_ratio is not None and old_ratio is not None:
        if new_ratio > 1.8 and old_ratio <= 1.8:
            candidates.add("NEW_SUSPECT_OLD_OK")
        if new_ratio <= 1.8 and old_ratio > 1.8:
            candidates.add("NEW_OK_OLD_SUSPECT")
        if new_ratio > 1.8 and old_ratio > 1.8:
            candidates.add("BOTH_SUSPECT")

    if distance_change_pct is not None:
        if distance_change_pct <= 0.15:
            candidates.add("CONSISTENT_WITH_OLD")
        elif distance_change_pct <= 0.30:
            candidates.add("WATCH_CHANGED")
        else:
            candidates.add("SUSPECT_CHANGED")

    for status in COMPARE_STATUS_ORDER:
        if status in candidates:
            return status
    return "UNKNOWN"


def recrawl_priority(status: str) -> str:
    if status in HIGH_PRIORITY:
        return "HIGH"
    if status in MEDIUM_PRIORITY:
        return "MEDIUM"
    if status in LOW_PRIORITY:
        return "LOW"
    return "MEDIUM"


def compare_frames(new_df: pd.DataFrame, old_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    old_indexes = build_old_indexes(old_df)
    matched_old_indices: set[int] = set()
    output_rows: list[dict[str, Any]] = []

    for _, new_row in new_df.iterrows():
        matched_by, old_idx = find_old_match(new_row, old_indexes)
        old_row = old_df.loc[old_idx] if old_idx is not None else None
        if old_idx is not None:
            matched_old_indices.add(old_idx)

        new_distance_km = parse_distance_km(new_row)
        old_distance_km = parse_distance_km(old_row) if old_row is not None else None
        new_duration = parse_duration(new_row)
        old_duration = parse_duration(old_row) if old_row is not None else None
        new_ratio = ratio_to_air(new_distance_km, new_row.get("khoang_cach_chim_bay"))
        old_air = old_row.get("khoang_cach_chim_bay") if old_row is not None else pd.NA
        old_ratio = ratio_to_air(old_distance_km, old_air)

        distance_diff = (
            round(new_distance_km - old_distance_km, 2)
            if new_distance_km is not None and old_distance_km is not None
            else None
        )
        distance_abs_diff = round(abs(distance_diff), 2) if distance_diff is not None else None
        distance_change_pct = (
            round(distance_abs_diff / old_distance_km, 4)
            if distance_abs_diff is not None and old_distance_km not in (None, 0)
            else None
        )

        status = choose_compare_status(
            matched_by=matched_by,
            new_distance_km=new_distance_km,
            old_distance_km=old_distance_km,
            new_ratio=new_ratio,
            old_ratio=old_ratio,
            distance_change_pct=distance_change_pct,
        )

        record = new_row.to_dict()
        record.update(
            {
                "matched_by": matched_by,
                "old_distance_km": old_distance_km,
                "new_distance_km": new_distance_km,
                "old_duration": old_duration,
                "new_duration": new_duration,
                "old_ratio_to_air": old_ratio,
                "new_ratio_to_air": new_ratio,
                "distance_diff_km": distance_diff,
                "distance_abs_diff_km": distance_abs_diff,
                "distance_change_pct": distance_change_pct,
                "compare_status": status,
                "recrawl_priority": recrawl_priority(status),
            }
        )
        output_rows.append(record)

    compare_df = pd.DataFrame(output_rows)
    old_not_in_new = old_df.loc[~old_df.index.isin(matched_old_indices)].copy()
    return compare_df, old_not_in_new


def make_summary(compare_df: pd.DataFrame, new_rows: int, old_rows: int, old_not_in_new_rows: int) -> pd.DataFrame:
    summary = [
        {"metric": "new_rows", "value": new_rows},
        {"metric": "old_rows", "value": old_rows},
        {
            "metric": "matched_by_code",
            "value": int(compare_df["matched_by"].isin(["directed_pair_key_by_code", "undirected_pair_key_by_code"]).sum()),
        },
        {
            "metric": "matched_by_coord",
            "value": int(compare_df["matched_by"].isin(["directed_pair_key_by_coord", "undirected_pair_key_by_coord"]).sum()),
        },
        {"metric": "no_old_baseline", "value": int((compare_df["matched_by"] == "NO_OLD_BASELINE").sum())},
        {"metric": "old_pairs_not_in_new", "value": old_not_in_new_rows},
    ]

    for status in COMPARE_STATUS_ORDER:
        summary.append(
            {
                "metric": f"status_{status}",
                "value": int((compare_df["compare_status"] == status).sum()),
            }
        )

    for priority in ["HIGH", "MEDIUM", "LOW"]:
        summary.append(
            {
                "metric": f"recrawl_priority_{priority}",
                "value": int((compare_df["recrawl_priority"] == priority).sum()),
            }
        )

    return pd.DataFrame(summary)


def write_outputs(compare_df: pd.DataFrame, summary_df: pd.DataFrame, old_not_in_new: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    compare_df.to_csv(output_dir / "compare_full_results.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(output_dir / "compare_summary.csv", index=False, encoding="utf-8-sig")
    compare_df.loc[compare_df["recrawl_priority"] == "HIGH"].to_csv(
        output_dir / "recrawl_high_priority.csv", index=False, encoding="utf-8-sig"
    )
    compare_df.loc[compare_df["recrawl_priority"] == "MEDIUM"].to_csv(
        output_dir / "recrawl_medium_priority.csv", index=False, encoding="utf-8-sig"
    )
    compare_df.loc[compare_df["matched_by"] == "NO_OLD_BASELINE"].to_csv(
        output_dir / "no_old_baseline_new_pairs.csv", index=False, encoding="utf-8-sig"
    )
    old_not_in_new.to_csv(output_dir / "old_pairs_not_in_new.csv", index=False, encoding="utf-8-sig")
    compare_df.sort_values("distance_abs_diff_km", ascending=False, na_position="last").head(200).to_csv(
        output_dir / "top_200_changed.csv", index=False, encoding="utf-8-sig"
    )
    compare_df.loc[compare_df["compare_status"] == "NEW_SUSPECT_OLD_OK"].to_csv(
        output_dir / "new_suspect_old_ok.csv", index=False, encoding="utf-8-sig"
    )


def print_summary(summary_df: pd.DataFrame, output_dir: Path) -> None:
    values = dict(zip(summary_df["metric"], summary_df["value"]))
    print(f"Output dir: {output_dir}")
    print(f"Total new rows: {values.get('new_rows', 0)}")
    print(f"Total old rows: {values.get('old_rows', 0)}")
    print(f"Matched by branch code: {values.get('matched_by_code', 0)}")
    print(f"Matched by coordinates: {values.get('matched_by_coord', 0)}")
    print(f"No old baseline: {values.get('no_old_baseline', 0)}")
    print(f"CONSISTENT_WITH_OLD: {values.get('status_CONSISTENT_WITH_OLD', 0)}")
    print(f"WATCH_CHANGED: {values.get('status_WATCH_CHANGED', 0)}")
    print(f"SUSPECT_CHANGED: {values.get('status_SUSPECT_CHANGED', 0)}")
    print(f"NEW_SUSPECT_OLD_OK: {values.get('status_NEW_SUSPECT_OLD_OK', 0)}")
    print(f"Need recrawl HIGH: {values.get('recrawl_priority_HIGH', 0)}")
    print(f"Old pairs not in new: {values.get('old_pairs_not_in_new', 0)}")


def main() -> None:
    args = parse_args()
    new_df = make_keys(standardize_columns(read_table(args.new_file))).reset_index(drop=True)
    old_df = make_keys(standardize_columns(read_table(args.old_file))).reset_index(drop=True)

    compare_df, old_not_in_new = compare_frames(new_df, old_df)
    summary_df = make_summary(
        compare_df=compare_df,
        new_rows=len(new_df),
        old_rows=len(old_df),
        old_not_in_new_rows=len(old_not_in_new),
    )

    write_outputs(compare_df, summary_df, old_not_in_new, args.output_dir)
    print_summary(summary_df, args.output_dir)


if __name__ == "__main__":
    main()
