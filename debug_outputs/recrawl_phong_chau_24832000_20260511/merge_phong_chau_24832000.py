#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path

import pandas as pd


CODE = "24832000"
NEW_LON = 105.2928010
NEW_LAT = 21.3392810

BASE = Path("debug_outputs/recrawl_phong_chau_24832000_20260511")
FINAL_INPUT = Path("data_20260504/final/road_distance_20260504_final_recrawl_ok_applied.xlsx")
RECRAWL_OUTPUT = BASE / "output" / "recrawl_results.csv"
if not RECRAWL_OUTPUT.exists():
    RECRAWL_OUTPUT = BASE / "output" / "recrawl_results_incremental.csv"

FINAL_OUTPUT_XLSX = Path("data_20260504/final/road_distance_20260504_final_recrawl_ok_applied_phong_chau_24832000.xlsx")
FINAL_OUTPUT_CSV = Path("data_20260504/final/road_distance_20260504_final_recrawl_ok_applied_phong_chau_24832000.csv")
AUDIT_OUTPUT_XLSX = Path("data_20260504/final/road_distance_20260504_final_recrawl_ok_applied_phong_chau_24832000_audit.xlsx")
SUMMARY_OUTPUT = BASE / "merge_summary.txt"


def clean_code(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True)


def main() -> None:
    if not RECRAWL_OUTPUT.exists():
        raise FileNotFoundError(f"Missing recrawl output: {RECRAWL_OUTPUT}")

    final = pd.read_excel(FINAL_INPUT)
    recrawl = pd.read_csv(RECRAWL_OUTPUT)

    if not final["global_index"].is_unique:
        raise ValueError("global_index is not unique in final input")
    if not recrawl["global_index"].is_unique:
        raise ValueError("global_index is not unique in recrawl output")

    final_code1 = clean_code(final["ma_phong_ban_1"]).eq(CODE)
    final_code2 = clean_code(final["ma_phong_ban_2"]).eq(CODE)
    target_mask = final_code1 | final_code2

    updated = final.copy()
    updated.loc[final_code1, "kinh_do_1"] = NEW_LON
    updated.loc[final_code1, "vi_do_1"] = NEW_LAT
    updated.loc[final_code2, "kinh_do_2"] = NEW_LON
    updated.loc[final_code2, "vi_do_2"] = NEW_LAT

    recrawl_cols = [
        "global_index",
        "recrawl_status",
        "recrawl_distance_text",
        "recrawl_distance_km",
        "recrawl_duration_text",
        "recrawl_attempts",
        "recrawl_screenshot_path",
    ]
    recrawl_cols = [col for col in recrawl_cols if col in recrawl.columns]
    joined = updated.merge(recrawl[recrawl_cols], on="global_index", how="left", validate="one_to_one")

    ok_mask = target_mask & joined["recrawl_status"].eq("OK") & joined["recrawl_distance_km"].notna()
    updated.loc[ok_mask, "Khoảng cách đường bộ"] = joined.loc[ok_mask, "recrawl_distance_text"].values
    updated.loc[ok_mask, "Khoảng cách đường bộ km"] = joined.loc[ok_mask, "recrawl_distance_km"].values
    updated.loc[ok_mask, "thời gian"] = joined.loc[ok_mask, "recrawl_duration_text"].values
    updated.loc[ok_mask, "crawl_status"] = "recrawled_phong_chau_ok"

    audit = updated.merge(recrawl[recrawl_cols], on="global_index", how="left", validate="one_to_one")
    audit["phong_chau_coord_updated"] = target_mask.values
    audit["phong_chau_distance_updated"] = ok_mask.values

    updated.to_excel(FINAL_OUTPUT_XLSX, index=False)
    updated.to_csv(FINAL_OUTPUT_CSV, index=False, encoding="utf-8-sig")
    audit.to_excel(AUDIT_OUTPUT_XLSX, index=False)

    status_counts = recrawl["recrawl_status"].fillna("<EMPTY>").value_counts().to_dict()
    summary = [
        f"final_input={FINAL_INPUT}",
        f"recrawl_output={RECRAWL_OUTPUT}",
        f"final_rows={len(final)}",
        f"target_rows_with_code={int(target_mask.sum())}",
        f"coord_updated_rows={int(target_mask.sum())}",
        f"distance_updated_ok_rows={int(ok_mask.sum())}",
        f"final_output_xlsx={FINAL_OUTPUT_XLSX}",
        f"final_output_csv={FINAL_OUTPUT_CSV}",
        f"audit_output_xlsx={AUDIT_OUTPUT_XLSX}",
        "recrawl_status_counts:",
    ]
    summary.extend(f"  {key}={value}" for key, value in status_counts.items())
    SUMMARY_OUTPUT.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
