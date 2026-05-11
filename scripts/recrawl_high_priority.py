#!/usr/bin/env python
"""Recrawl suspect Google Maps routes from a CSV input file."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


ATTEMPTS_PER_ROW = 3
INCREMENTAL_EVERY = 50
ROUTE_PANEL_SELECTORS = [
    "div[role='main']",
    "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
    "body",
]
ROUTE_TEXT_SELECTORS = [
    *config.GOOGLE_MAPS_SELECTORS,
    "div[role='main'] div[aria-label*='hour']",
    "div[role='main'] div[aria-label*='minute']",
    "div[role='main']",
]
DISTANCE_RE = re.compile(r"(?P<num>\d+(?:[,.]\d+)?)\s*(?P<unit>km|m)\b", re.I)
DURATION_RE = re.compile(
    r"(?:(?:\d+\s*(?:hr|hour|hours|h|giờ|gio))\s*)?\d+\s*(?:min|mins|minute|minutes|phút|phut)\b|"
    r"\d+\s*(?:hr|hour|hours|h|giờ|gio)\b",
    re.I,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--machine-id", type=str, required=True)
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing recrawl output files.")
    parser.add_argument("--max-rows", type=int, default=None, help="Optional smoke-test row limit.")
    parser.add_argument("--sleep-time", type=float, default=float(config.CRAWL_DEFAULTS["SLEEP_TIME"]))
    parser.add_argument("--wait-time", type=int, default=max(30, int(config.CRAWL_DEFAULTS["WAIT_TIME"])))
    return parser.parse_args()


def setup_logging(output_dir: Path, machine_id: str) -> logging.Logger:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f"recrawl_{machine_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logger = logging.getLogger("recrawl_high_priority")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(config.LOG_FORMAT, datefmt=config.LOG_DATE_FORMAT)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def compact_text(value: str | None) -> str:
    return " ".join(str(value or "").split())


def parse_distance(value: str | None) -> tuple[str | None, float | None, list[str]]:
    text = str(value or "")
    matches = list(DISTANCE_RE.finditer(text))
    all_distance_texts = [match.group(0) for match in matches]
    if not matches:
        return None, None, all_distance_texts

    match = matches[-1]
    number = float(match.group("num").replace(",", "."))
    unit = match.group("unit").lower()
    km = number if unit == "km" else number / 1000
    return match.group(0), round(km, 2), all_distance_texts


def parse_duration(value: str | None) -> str | None:
    match = DURATION_RE.search(str(value or ""))
    return match.group(0) if match else None


def build_url(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> str:
    return f"https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}/data=!4m2!4m1!3e0"


def setup_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def get_first_text(driver: webdriver.Chrome, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            for element in driver.find_elements(By.CSS_SELECTOR, selector):
                text = element.text.strip()
                if text:
                    return text
        except Exception:
            continue
    return ""


def get_route_candidates(driver: webdriver.Chrome) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for selector in ROUTE_TEXT_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            continue
        for index, element in enumerate(elements):
            text = element.text.strip()
            normalized = compact_text(text)
            if not normalized or normalized in seen:
                continue
            if DISTANCE_RE.search(text) and DURATION_RE.search(text):
                candidates.append({"selector": selector, "index": index, "text": text})
                seen.add(normalized)
    return candidates


def wait_for_route_ready(driver: webdriver.Chrome, wait_time: int) -> tuple[str, list[dict[str, Any]]]:
    def ready(current_driver: webdriver.Chrome):
        panel_text = get_first_text(current_driver, ROUTE_PANEL_SELECTORS)
        candidates = get_route_candidates(current_driver)
        if panel_text and DISTANCE_RE.search(panel_text) and DURATION_RE.search(panel_text) and candidates:
            return panel_text, candidates
        if panel_text and config.ERROR_KEYWORDS.search(panel_text):
            return panel_text, candidates
        return False

    try:
        return WebDriverWait(driver, wait_time).until(ready)
    except Exception:
        return get_first_text(driver, ROUTE_PANEL_SELECTORS), get_route_candidates(driver)


def build_status(
    route_panel_raw_text: str,
    selected_route_raw_text: str,
    parsed_distance_km: float | None,
    air_distance_km: float | None,
    previous_route_raw_text: str | None,
) -> str:
    statuses: list[str] = []
    if parsed_distance_km is None:
        statuses.append("PARSE_FAILED")
    if not DISTANCE_RE.search(route_panel_raw_text) or not DURATION_RE.search(route_panel_raw_text):
        statuses.append("ROUTE_NOT_READY")
    if (
        parsed_distance_km is not None
        and air_distance_km is not None
        and air_distance_km > 0
        and parsed_distance_km / air_distance_km > 1.8
    ):
        statuses.append("SUSPECT_DISTANCE")
    if previous_route_raw_text and compact_text(previous_route_raw_text) == compact_text(selected_route_raw_text):
        statuses.append("POSSIBLE_STALE_ROUTE")
    return "|".join(statuses) if statuses else "OK"


def capture_screenshot(driver: webdriver.Chrome, output_dir: Path, row_index: int, attempt: int) -> str:
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot = screenshot_dir / f"row_{row_index:05d}_attempt_{attempt}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    driver.save_screenshot(str(screenshot))
    try:
        return str(screenshot.relative_to(config.PROJECT_ROOT))
    except ValueError:
        return str(screenshot)


def run_attempt(
    driver: webdriver.Chrome,
    row: pd.Series,
    row_index: int,
    attempt: int,
    previous_route_raw_text: str | None,
    output_dir: Path,
    wait_time: int,
) -> dict[str, Any]:
    lat1, lon1 = row["vi_do_1"], row["kinh_do_1"]
    lat2, lon2 = row["vi_do_2"], row["kinh_do_2"]
    air_distance_km = pd.to_numeric(row.get("khoang_cach_chim_bay"), errors="coerce")
    if pd.isna(air_distance_km):
        air_distance_km = None

    url = build_url(lat1, lon1, lat2, lon2)
    timestamp = datetime.now().isoformat(timespec="seconds")
    driver.get(url)

    route_panel_raw_text, candidates = wait_for_route_ready(driver, wait_time)
    selected = candidates[0] if candidates else {"index": None, "text": "", "selector": None}
    selected_route_raw_text = selected["text"]
    parsed_distance_text, parsed_distance_km, all_distance_texts = parse_distance(selected_route_raw_text)
    parsed_duration_text = parse_duration(selected_route_raw_text)
    status_check = build_status(
        route_panel_raw_text=route_panel_raw_text,
        selected_route_raw_text=selected_route_raw_text,
        parsed_distance_km=parsed_distance_km,
        air_distance_km=float(air_distance_km) if air_distance_km is not None else None,
        previous_route_raw_text=previous_route_raw_text,
    )

    screenshot_path = None
    if status_check != "OK":
        screenshot_path = capture_screenshot(driver, output_dir, row_index, attempt)

    return {
        "attempt": attempt,
        "origin_input": f"{lat1},{lon1}",
        "destination_input": f"{lat2},{lon2}",
        "google_maps_url": url,
        "crawl_timestamp": timestamp,
        "current_url_after_load": driver.current_url,
        "page_title": driver.title,
        "route_panel_raw_text": route_panel_raw_text,
        "selected_route_index": selected["index"],
        "selected_route_selector": selected["selector"],
        "selected_route_raw_text": selected_route_raw_text,
        "parsed_distance_text": parsed_distance_text,
        "parsed_duration_text": parsed_duration_text,
        "parsed_distance_km": parsed_distance_km,
        "all_distance_texts": all_distance_texts,
        "screenshot_path": screenshot_path,
        "status_check": status_check,
    }


def choose_best_attempt(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    ok_attempts = [attempt for attempt in attempts if attempt.get("status_check") == "OK"]
    if ok_attempts:
        return ok_attempts[-1]
    parsed_attempts = [attempt for attempt in attempts if attempt.get("parsed_distance_km") is not None]
    if parsed_attempts:
        return parsed_attempts[-1]
    return attempts[-1]


def ensure_output_is_writable(output_dir: Path, overwrite: bool) -> None:
    existing_outputs = [
        output_dir / "recrawl_results.csv",
        output_dir / "recrawl_results.xlsx",
        output_dir / "recrawl_results_incremental.csv",
    ]
    found = [path for path in existing_outputs if path.exists()]
    if found and not overwrite:
        found_text = "\n".join(str(path) for path in found)
        raise FileExistsError(
            "Output đã tồn tại. Dùng --overwrite nếu muốn ghi đè:\n"
            f"{found_text}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def save_outputs(df: pd.DataFrame, output_dir: Path, final: bool) -> None:
    csv_path = output_dir / ("recrawl_results.csv" if final else "recrawl_results_incremental.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    if final:
        df.to_excel(output_dir / "recrawl_results.xlsx", index=False)


def main() -> None:
    args = parse_args()
    ensure_output_is_writable(args.output_dir, args.overwrite)
    logger = setup_logging(args.output_dir, args.machine_id)

    if not args.input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy input file: {args.input_file}")

    df = pd.read_csv(args.input_file, encoding="utf-8-sig")
    if args.max_rows is not None:
        df = df.head(args.max_rows).copy()
    df = df.reset_index(drop=True)

    required = ["vi_do_1", "kinh_do_1", "vi_do_2", "kinh_do_2"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Input thiếu cột tọa độ: {', '.join(missing)}")

    for column in [
        "recrawl_machine_id",
        "recrawl_attempts",
        "recrawl_status",
        "recrawl_distance_text",
        "recrawl_distance_km",
        "recrawl_duration_text",
        "recrawl_raw_text",
        "recrawl_screenshot_path",
        "recrawl_attempts_json",
    ]:
        if column not in df.columns:
            df[column] = None

    logger.info("Starting recrawl: machine_id=%s rows=%s input=%s", args.machine_id, len(df), args.input_file)
    driver = setup_driver()
    processed_since_save = 0
    previous_route_raw_text: str | None = None
    try:
        for idx, row in df.iterrows():
            attempts: list[dict[str, Any]] = []
            for attempt_num in range(1, ATTEMPTS_PER_ROW + 1):
                try:
                    attempt_result = run_attempt(
                        driver=driver,
                        row=row,
                        row_index=idx,
                        attempt=attempt_num,
                        previous_route_raw_text=previous_route_raw_text,
                        output_dir=args.output_dir,
                        wait_time=args.wait_time,
                    )
                except Exception as exc:
                    logger.warning("Row %s attempt %s failed: %s", idx, attempt_num, exc)
                    attempt_result = {
                        "attempt": attempt_num,
                        "status_check": "ERROR",
                        "error": str(exc),
                        "crawl_timestamp": datetime.now().isoformat(timespec="seconds"),
                    }
                attempts.append(attempt_result)
                previous_route_raw_text = str(attempt_result.get("selected_route_raw_text") or "")
                if attempt_result.get("status_check") == "OK":
                    break
                time.sleep(args.sleep_time)

            best = choose_best_attempt(attempts)
            df.at[idx, "recrawl_machine_id"] = args.machine_id
            df.at[idx, "recrawl_attempts"] = len(attempts)
            df.at[idx, "recrawl_status"] = best.get("status_check")
            df.at[idx, "recrawl_distance_text"] = best.get("parsed_distance_text")
            df.at[idx, "recrawl_distance_km"] = best.get("parsed_distance_km")
            df.at[idx, "recrawl_duration_text"] = best.get("parsed_duration_text")
            df.at[idx, "recrawl_raw_text"] = best.get("selected_route_raw_text") or best.get("route_panel_raw_text")
            df.at[idx, "recrawl_screenshot_path"] = best.get("screenshot_path")
            df.at[idx, "recrawl_attempts_json"] = json.dumps(attempts, ensure_ascii=False)

            logger.info(
                "Row %s/%s status=%s distance=%s duration=%s attempts=%s",
                idx + 1,
                len(df),
                best.get("status_check"),
                best.get("parsed_distance_km"),
                best.get("parsed_duration_text"),
                len(attempts),
            )
            processed_since_save += 1
            if processed_since_save >= INCREMENTAL_EVERY:
                save_outputs(df, args.output_dir, final=False)
                logger.info("Saved incremental output after row %s", idx + 1)
                processed_since_save = 0

            time.sleep(args.sleep_time)
    finally:
        driver.quit()

    save_outputs(df, args.output_dir, final=True)
    logger.info("Completed recrawl. Output dir: %s", args.output_dir)


if __name__ == "__main__":
    main()
