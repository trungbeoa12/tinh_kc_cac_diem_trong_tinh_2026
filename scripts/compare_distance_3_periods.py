#!/usr/bin/env python3
"""Compare road-distance crawl results across three periods.

This script does not run or modify the crawler. It reuses the existing
build_crawl_pairs module to generate current same-province branch pairs.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_crawl_pairs
import config


LOGGER = logging.getLogger("compare_distance_3_periods")

PERIOD_FILES = {
    "20250520": "20250520.xlsx",
    "20260312": "20260312.xlsx",
    "20260504": "20260504.xlsx",
}
BRANCHES_FILE = "branches_20260504.xlsx"

DEFAULT_DATA_DIR = config.PROJECT_ROOT / "data_20260504_ver2"
DEFAULT_OUTPUT_DIR = config.PROJECT_ROOT / "outputs" / "compare_distance_3_periods"

MATCHED = "MATCHED_3_PERIODS"
CHANGED = "DISTANCE_CHANGED"
MISSING = "MISSING_IN_ONE_OR_MORE_PERIODS"

RESULT_COLUMNS = [
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
    "distance_km",
    "distance_raw",
    "duration",
]

COLUMN_ALIASES = {
    "ma_phong_ban_1": [
        "ma_phong_ban_1",
        "ma phong ban 1",
        "ma phong ban dau",
        "ma phong ban di",
        "ma don vi 1",
    ],
    "ten_phong_ban_1": [
        "ten_phong_ban_1",
        "ten phong ban 1",
        "ten phong ban dau",
        "ten phong ban di",
        "ten don vi 1",
    ],
    "kinh_do_1": ["kinh_do_1", "kinh do 1", "longitude 1", "lon 1", "lng 1"],
    "vi_do_1": ["vi_do_1", "vi do 1", "latitude 1", "lat 1"],
    "ma_phong_ban_2": [
        "ma_phong_ban_2",
        "ma phong ban 2",
        "ma phong ban cuoi",
        "ma phong ban den",
        "ma don vi 2",
    ],
    "ten_phong_ban_2": [
        "ten_phong_ban_2",
        "ten phong ban 2",
        "ten phong ban cuoi",
        "ten phong ban den",
        "ten don vi 2",
    ],
    "kinh_do_2": ["kinh_do_2", "kinh do 2", "longitude 2", "lon 2", "lng 2"],
    "vi_do_2": ["vi_do_2", "vi do 2", "latitude 2", "lat 2"],
    "tinh_thanh": [
        "tinh_thanh",
        "tinh thanh",
        "tinh",
        "province",
        "tinh thanh sau sap nhap",
    ],
    "khoang_cach_chim_bay": [
        "khoang_cach_chim_bay",
        "khoang_cach_chim_bay_km",
        "khoang cach chim bay",
        "khoang cach chim bay km",
        "air distance km",
    ],
    "distance_km": [
        "khoang cach duong bo km",
        "khoang_cach_duong_bo_km",
        "road distance km",
        "distance km",
        "distance_km",
        "parsed_distance_km",
    ],
    "distance_raw": [
        "khoang cach duong bo",
        "khoang_cach_duong_bo",
        "khoang cach duong bo raw",
        "road distance",
        "distance",
        "parsed_distance_text",
    ],
    "duration": ["thoi gian", "thời gian", "duration", "time", "parsed_duration_text"],
}

DISTANCE_WITH_UNIT_RE = re.compile(r"(?P<num>\d+(?:[,.]\d+)?)\s*(?P<unit>km|m)\b", re.I)
NUMBER_RE = re.compile(r"\d+(?:[,.]\d+)?")


@dataclass(frozen=True)
class PeriodData:
    period: str
    path: Path
    raw: pd.DataFrame
    standardized: pd.DataFrame
    unique_pairs: pd.DataFrame
    duplicate_rows: pd.DataFrame


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--branches-file", type=Path)
    return parser.parse_args()


def normalize_label(value: object) -> str:
    text = str(value or "").strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        lookup[normalize_label(canonical)] = canonical
        for alias in aliases:
            lookup[normalize_label(alias)] = canonical
    return lookup


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


def parse_number(value: object) -> float | None:
    if is_missing(value):
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+(?:[,.]\d+)?", text):
        return float(text.replace(",", "."))
    return None


def parse_distance_km(row: pd.Series) -> float | None:
    explicit = parse_number(row.get("distance_km"))
    if explicit is not None:
        return round(explicit, 2)

    raw = row.get("distance_raw")
    raw_number = parse_number(raw)
    if raw_number is not None:
        return round(raw_number, 2)
    if is_missing(raw):
        return None

    text = str(raw)
    matches = list(DISTANCE_WITH_UNIT_RE.finditer(text))
    if matches:
        match = matches[-1]
        value = float(match.group("num").replace(",", "."))
        if match.group("unit").lower() == "m":
            value = value / 1000
        return round(value, 2)

    number_match = NUMBER_RE.search(text)
    if number_match:
        return round(float(number_match.group(0).replace(",", ".")), 2)
    return None


def make_pair_key(code1: object, code2: object) -> str:
    left = normalize_code(code1)
    right = normalize_code(code2)
    if not left or not right:
        raise ValueError(f"Cannot build pair_key from missing codes: {code1!r}, {code2!r}")
    return "__".join(sorted([left, right]))


def make_pair_key_from_row(row: pd.Series) -> str:
    return make_pair_key(row["ma_phong_ban_1"], row["ma_phong_ban_2"])


def reorder_pair_columns(row: pd.Series) -> dict[str, Any]:
    code1 = normalize_code(row.get("ma_phong_ban_1"))
    code2 = normalize_code(row.get("ma_phong_ban_2"))
    if not code1 or not code2:
        raise ValueError("Cannot reorder pair with missing branch code")

    if code1 <= code2:
        return {
            "ma_phong_ban_1": code1,
            "ten_phong_ban_1": row.get("ten_phong_ban_1"),
            "kinh_do_1": row.get("kinh_do_1"),
            "vi_do_1": row.get("vi_do_1"),
            "ma_phong_ban_2": code2,
            "ten_phong_ban_2": row.get("ten_phong_ban_2"),
            "kinh_do_2": row.get("kinh_do_2"),
            "vi_do_2": row.get("vi_do_2"),
        }
    return {
        "ma_phong_ban_1": code2,
        "ten_phong_ban_1": row.get("ten_phong_ban_2"),
        "kinh_do_1": row.get("kinh_do_2"),
        "vi_do_1": row.get("vi_do_2"),
        "ma_phong_ban_2": code1,
        "ten_phong_ban_2": row.get("ten_phong_ban_1"),
        "kinh_do_2": row.get("kinh_do_1"),
        "vi_do_2": row.get("vi_do_1"),
    }


def standardize_result_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = build_alias_lookup()
    renamed: dict[str, str] = {}
    used: set[str] = set()
    for column in df.columns:
        canonical = aliases.get(normalize_label(column))
        if canonical and canonical not in used:
            renamed[column] = canonical
            used.add(canonical)

    result = df.rename(columns=renamed).copy()
    for column in RESULT_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    key_nulls = {
        column: int(result[column].apply(normalize_code).isna().sum())
        for column in ["ma_phong_ban_1", "ma_phong_ban_2"]
    }
    if any(key_nulls.values()):
        raise ValueError(f"Missing result key values: {key_nulls}")

    result["distance_km"] = result.apply(parse_distance_km, axis=1)
    result["pair_key"] = result.apply(make_pair_key_from_row, axis=1)
    result["pair_key_source"] = "sorted(ma_phong_ban_1, ma_phong_ban_2)"
    return result


def read_period(path: Path, period: str) -> PeriodData:
    LOGGER.info("Reading period %s: %s", period, path)
    raw = pd.read_excel(path)
    standardized = standardize_result_columns(raw)
    duplicate_mask = standardized["pair_key"].duplicated(keep=False)
    duplicate_rows = standardized.loc[duplicate_mask].copy()
    unique_pairs = (
        standardized.sort_values(["pair_key"])
        .drop_duplicates("pair_key", keep="first")
        .reset_index(drop=True)
    )
    LOGGER.info(
        "Period %s rows=%s unique_pairs=%s duplicate_pair_rows=%s",
        period,
        len(raw),
        len(unique_pairs),
        len(duplicate_rows),
    )
    return PeriodData(period, path, raw, standardized, unique_pairs, duplicate_rows)


def inspect_excel_file(path: Path) -> pd.DataFrame:
    xl = pd.ExcelFile(path)
    rows: list[dict[str, Any]] = []
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet_name)
        rows.append(
            {
                "file": path.name,
                "sheet": sheet_name,
                "rows": len(df),
                "columns": ", ".join(map(str, df.columns)),
            }
        )
    return pd.DataFrame(rows)


def build_key_report(periods: dict[str, PeriodData], branches_path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for period, data in periods.items():
        duplicate_pair_keys = int(
            data.standardized.loc[
                data.standardized["pair_key"].duplicated(keep=False), "pair_key"
            ].nunique()
        )
        rows.append(
            {
                "file": data.path.name,
                "period": period,
                "unit_identifier_columns": "ma_phong_ban_1, ma_phong_ban_2",
                "distance_column_used": "distance_km parsed from road-distance km/text columns",
                "pair_key_rule": "undirected sorted pair of department codes",
                "rows": len(data.raw),
                "unique_pair_keys": data.standardized["pair_key"].nunique(),
                "duplicate_pair_keys": duplicate_pair_keys,
                "duplicate_pair_rows": len(data.duplicate_rows),
            }
        )

    points = build_crawl_pairs.load_points(branches_path)
    rows.append(
        {
            "file": branches_path.name,
            "period": "current_branches",
            "unit_identifier_columns": "Mã phòng ban",
            "distance_column_used": "",
            "pair_key_rule": "undirected sorted pair of department codes",
            "rows": len(points),
            "unique_pair_keys": "",
            "duplicate_pair_keys": int(points["ma_phong_ban"].duplicated().sum()),
            "duplicate_pair_rows": "",
        }
    )
    return pd.DataFrame(rows)


def choose_reference_row(pair_key: str, lookups: dict[str, pd.DataFrame]) -> pd.Series:
    for period in sorted(lookups, reverse=True):
        if pair_key in lookups[period].index:
            return lookups[period].loc[pair_key]
    raise KeyError(pair_key)


def compare_periods(periods: dict[str, PeriodData]) -> pd.DataFrame:
    lookups = {
        period: data.unique_pairs.set_index("pair_key", drop=False)
        for period, data in periods.items()
    }
    all_keys = sorted(set.union(*(set(data.unique_pairs["pair_key"]) for data in periods.values())))
    rows: list[dict[str, Any]] = []

    for pair_key in all_keys:
        ref = choose_reference_row(pair_key, lookups)
        record: dict[str, Any] = {"pair_key": pair_key, **reorder_pair_columns(ref)}
        record["tinh_thanh"] = ref.get("tinh_thanh")
        record["khoang_cach_chim_bay"] = ref.get("khoang_cach_chim_bay")

        distances: list[float | None] = []
        present_count = 0
        present_periods: list[str] = []
        for period in sorted(periods):
            exists = pair_key in lookups[period].index
            record[f"exists_{period}"] = exists
            if exists:
                present_count += 1
                present_periods.append(period)
                period_row = lookups[period].loc[pair_key]
                distance = period_row.get("distance_km")
                record[f"distance_{period}"] = distance
                record[f"distance_raw_{period}"] = period_row.get("distance_raw")
                distances.append(None if is_missing(distance) else float(distance))
            else:
                record[f"distance_{period}"] = pd.NA
                record[f"distance_raw_{period}"] = pd.NA
                distances.append(None)

        record["period_count"] = present_count
        record["present_periods"] = ",".join(present_periods)
        record["exists_all_3_periods"] = present_count == 3
        if present_count == 3 and all(distance is not None for distance in distances):
            unique_distances = {round(float(distance), 2) for distance in distances if distance is not None}
            same_distance = len(unique_distances) == 1
            record["max_distance_diff"] = round(
                max(float(distance) for distance in distances if distance is not None)
                - min(float(distance) for distance in distances if distance is not None),
                2,
            )
        else:
            same_distance = False
            record["max_distance_diff"] = pd.NA

        record["same_distance_all_3_periods"] = same_distance
        if same_distance:
            record["compare_status"] = MATCHED
        elif present_count == 3:
            record["compare_status"] = CHANGED
        else:
            record["compare_status"] = MISSING
        rows.append(record)

    return pd.DataFrame(rows)


def build_all_pairs_from_branches(branches_path: Path) -> pd.DataFrame:
    LOGGER.info("Building all current pairs from branches with existing project logic: %s", branches_path)
    points = build_crawl_pairs.load_points(branches_path)
    pairs = build_crawl_pairs.build_same_province_pairs(points)
    pairs["pair_key"] = pairs.apply(make_pair_key_from_row, axis=1)
    pairs["pair_key_source"] = "sorted(ma_phong_ban_1, ma_phong_ban_2)"
    return pairs.sort_values(["tinh_thanh", "ma_phong_ban_1", "ma_phong_ban_2"]).reset_index(drop=True)


def split_current_pairs(
    all_pairs: pd.DataFrame,
    matched: pd.DataFrame,
    comparison: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    matched_keys = set(matched["pair_key"])
    status_by_key = dict(zip(comparison["pair_key"], comparison["compare_status"]))

    stable = all_pairs.loc[all_pairs["pair_key"].isin(matched_keys)].copy()
    recrawl = all_pairs.loc[~all_pairs["pair_key"].isin(matched_keys)].copy()

    def reason(pair_key: str) -> str:
        status = status_by_key.get(pair_key)
        if status == CHANGED:
            return "DISTANCE_CHANGED_ACROSS_PERIODS"
        if status == MISSING:
            return "MISSING_IN_ONE_OR_MORE_PERIODS"
        return "NEW_PAIR_FROM_CURRENT_BRANCHES"

    recrawl["recrawl_reason"] = recrawl["pair_key"].map(reason)
    return stable.reset_index(drop=True), recrawl.reset_index(drop=True)


def build_summary(
    periods: dict[str, PeriodData],
    comparison: pd.DataFrame,
    all_pairs: pd.DataFrame,
    stable: pd.DataFrame,
    recrawl: pd.DataFrame,
) -> pd.DataFrame:
    status_counts = comparison["compare_status"].value_counts().to_dict()
    rows: list[dict[str, Any]] = []
    for period in sorted(periods):
        data = periods[period]
        duplicate_pair_keys = int(
            data.standardized.loc[
                data.standardized["pair_key"].duplicated(keep=False), "pair_key"
            ].nunique()
        )
        rows.extend(
            [
                {"metric": f"{period}_rows", "value": len(data.raw)},
                {"metric": f"{period}_unique_pairs", "value": len(data.unique_pairs)},
                {"metric": f"{period}_duplicate_pair_keys", "value": duplicate_pair_keys},
                {"metric": f"{period}_duplicate_pair_rows", "value": len(data.duplicate_rows)},
            ]
        )

    rows.extend(
        [
            {"metric": "pairs_exists_all_3_periods", "value": int(comparison["exists_all_3_periods"].sum())},
            {"metric": "pairs_matched_pair_and_distance_all_3_periods", "value": int(status_counts.get(MATCHED, 0))},
            {"metric": "pairs_distance_changed", "value": int(status_counts.get(CHANGED, 0))},
            {"metric": "pairs_missing_in_one_or_more_periods", "value": int(status_counts.get(MISSING, 0))},
            {"metric": "all_pairs_from_current_branches", "value": len(all_pairs)},
            {"metric": "current_pairs_stable_no_need_recrawl", "value": len(stable)},
            {"metric": "current_pairs_need_recrawl", "value": len(recrawl)},
            {
                "metric": "current_pairs_recrawl_distance_changed",
                "value": int((recrawl["recrawl_reason"] == "DISTANCE_CHANGED_ACROSS_PERIODS").sum())
                if len(recrawl)
                else 0,
            },
            {
                "metric": "current_pairs_recrawl_missing_history",
                "value": int((recrawl["recrawl_reason"] == "MISSING_IN_ONE_OR_MORE_PERIODS").sum())
                if len(recrawl)
                else 0,
            },
            {
                "metric": "current_pairs_recrawl_new_pair",
                "value": int((recrawl["recrawl_reason"] == "NEW_PAIR_FROM_CURRENT_BRANCHES").sum())
                if len(recrawl)
                else 0,
            },
        ]
    )
    return pd.DataFrame(rows)


def write_outputs(
    output_dir: Path,
    comparison: pd.DataFrame,
    matched: pd.DataFrame,
    not_matched: pd.DataFrame,
    all_pairs: pd.DataFrame,
    stable: pd.DataFrame,
    recrawl: pd.DataFrame,
    summary: pd.DataFrame,
    schema: pd.DataFrame,
    key_report: pd.DataFrame,
    periods: dict[str, PeriodData],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_excel(output_dir / "doi_soat_3ky.xlsx", index=False, sheet_name="doi_soat_3ky")
    matched.to_excel(output_dir / "khop_3ky.xlsx", index=False, sheet_name="khop_3ky")
    not_matched.to_excel(output_dir / "khong_khop_3ky.xlsx", index=False, sheet_name="khong_khop_3ky")
    all_pairs.to_excel(output_dir / "all_pairs_from_branches_20260504.xlsx", index=False, sheet_name="all_pairs")
    stable.to_excel(
        output_dir / "pairs_stable_no_need_recrawl.xlsx",
        index=False,
        sheet_name="stable_no_recrawl",
    )
    recrawl.to_excel(output_dir / "pairs_need_recrawl.xlsx", index=False, sheet_name="need_recrawl")

    with pd.ExcelWriter(output_dir / "summary_compare_3_periods.xlsx") as writer:
        summary.to_excel(writer, index=False, sheet_name="summary")
        schema.to_excel(writer, index=False, sheet_name="schema")
        key_report.to_excel(writer, index=False, sheet_name="keys")
        comparison["compare_status"].value_counts().rename_axis("compare_status").reset_index(
            name="count"
        ).to_excel(writer, index=False, sheet_name="status_counts")
        recrawl["recrawl_reason"].value_counts().rename_axis("recrawl_reason").reset_index(
            name="count"
        ).to_excel(writer, index=False, sheet_name="recrawl_reasons")
        for period, data in periods.items():
            data.duplicate_rows.to_excel(writer, index=False, sheet_name=f"duplicates_{period}"[:31])


def print_summary(summary: pd.DataFrame, schema: pd.DataFrame, output_dir: Path) -> None:
    values = dict(zip(summary["metric"], summary["value"]))
    print("\n=== DATA SURVEY ===")
    for _, row in schema.iterrows():
        print(f"{row['file']} | sheet={row['sheet']} | rows={row['rows']} | columns={row['columns']}")

    print("\n=== SUMMARY ===")
    for period in sorted(PERIOD_FILES):
        print(
            f"{period}: unique_pairs={values.get(f'{period}_unique_pairs', 0)}, "
            f"duplicate_pair_keys={values.get(f'{period}_duplicate_pair_keys', 0)}, "
            f"duplicate_pair_rows={values.get(f'{period}_duplicate_pair_rows', 0)}"
        )
    print(f"Pairs appearing in all 3 periods: {values.get('pairs_exists_all_3_periods', 0)}")
    print(
        "Pairs matched by pair + normalized distance in all 3 periods: "
        f"{values.get('pairs_matched_pair_and_distance_all_3_periods', 0)}"
    )
    print(f"Pairs with distance changed: {values.get('pairs_distance_changed', 0)}")
    print(f"Pairs missing in one or more periods: {values.get('pairs_missing_in_one_or_more_periods', 0)}")
    print(f"All current pairs from branches: {values.get('all_pairs_from_current_branches', 0)}")
    print(f"Current pairs stable/no recrawl: {values.get('current_pairs_stable_no_need_recrawl', 0)}")
    print(f"Current pairs need recrawl: {values.get('current_pairs_need_recrawl', 0)}")
    print(f"Output dir: {output_dir}")
    print(f"khop_3ky: {output_dir / 'khop_3ky.xlsx'}")
    print(f"Need recrawl: {output_dir / 'pairs_need_recrawl.xlsx'}")


def main() -> None:
    setup_logging()
    args = parse_args()
    data_dir = args.data_dir
    output_dir = args.output_dir
    branches_path = args.branches_file or data_dir / BRANCHES_FILE

    LOGGER.info("Data dir: %s", data_dir)
    LOGGER.info("Output dir: %s", output_dir)

    period_paths = {period: data_dir / filename for period, filename in PERIOD_FILES.items()}
    for path in [*period_paths.values(), branches_path]:
        if not path.exists():
            raise FileNotFoundError(path)

    schema = pd.concat(
        [inspect_excel_file(path) for path in [*period_paths.values(), branches_path]],
        ignore_index=True,
    )
    periods = {period: read_period(path, period) for period, path in period_paths.items()}
    key_report = build_key_report(periods, branches_path)

    LOGGER.info("Comparing historical periods")
    comparison = compare_periods(periods)
    matched = comparison.loc[comparison["compare_status"] == MATCHED].copy().reset_index(drop=True)
    not_matched = comparison.loc[comparison["compare_status"] != MATCHED].copy().reset_index(drop=True)

    all_pairs = build_all_pairs_from_branches(branches_path)
    stable, recrawl = split_current_pairs(all_pairs, matched, comparison)
    summary = build_summary(periods, comparison, all_pairs, stable, recrawl)

    write_outputs(
        output_dir=output_dir,
        comparison=comparison,
        matched=matched,
        not_matched=not_matched,
        all_pairs=all_pairs,
        stable=stable,
        recrawl=recrawl,
        summary=summary,
        schema=schema,
        key_report=key_report,
        periods=periods,
    )
    print_summary(summary, schema, output_dir)


if __name__ == "__main__":
    main()
