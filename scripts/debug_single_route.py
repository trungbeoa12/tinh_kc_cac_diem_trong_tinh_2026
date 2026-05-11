#!/usr/bin/env python
"""Run one Google Maps route as a repeatable debug case.

This script intentionally does not change the batch crawler. It loads a direct
coordinate URL three times, captures raw route text, parsed values, screenshots,
and writes debug JSON/CSV artifacts for diagnosing stale DOM/selector/parse
issues.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


ORIGIN_LAT = 11.29029
ORIGIN_LON = 106.7955924
DESTINATION_LAT = 10.75028
DESTINATION_LON = 106.61129
AIR_DISTANCE_KM = 63.32622869
ATTEMPTS = 3
WAIT_TIME = 30

OUTPUT_DIR = config.PROJECT_ROOT / "debug_outputs"
SCREENSHOT_DIR = config.PROJECT_ROOT / "debug_screenshots"

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


def compact_text(value: str | None) -> str:
    return " ".join(str(value or "").split())


def build_url(origin_input: str, destination_input: str) -> str:
    return f"https://www.google.com/maps/dir/{origin_input}/{destination_input}/data=!4m2!4m1!3e0"


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
    for selector in ROUTE_TEXT_SELECTORS:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            continue
        for index, element in enumerate(elements):
            text = element.text.strip()
            if text and DISTANCE_RE.search(text) and DURATION_RE.search(text):
                candidates.append({"selector": selector, "index": index, "text": text})
    return candidates


def wait_for_route_ready(driver: webdriver.Chrome) -> tuple[str, list[dict[str, Any]]]:
    def ready(current_driver: webdriver.Chrome):
        panel_text = get_first_text(current_driver, ROUTE_PANEL_SELECTORS)
        candidates = get_route_candidates(current_driver)
        has_distance = bool(DISTANCE_RE.search(panel_text))
        has_duration = bool(DURATION_RE.search(panel_text))
        has_route_text = any(compact_text(item["text"]) for item in candidates)
        if panel_text and has_distance and has_duration and has_route_text:
            return panel_text, candidates
        return False

    return WebDriverWait(driver, WAIT_TIME).until(ready)


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


def build_status(
    route_panel_raw_text: str,
    selected_route_raw_text: str,
    parsed_distance_km: float | None,
    previous_raw_text: str | None,
) -> str:
    statuses: list[str] = []

    if parsed_distance_km is None:
        statuses.append("PARSE_FAILED")

    if not DISTANCE_RE.search(route_panel_raw_text) or not DURATION_RE.search(route_panel_raw_text):
        statuses.append("ROUTE_NOT_READY")

    if parsed_distance_km is not None and parsed_distance_km / AIR_DISTANCE_KM > 1.8:
        statuses.append("SUSPECT_DISTANCE")

    if previous_raw_text and compact_text(previous_raw_text) == compact_text(selected_route_raw_text):
        statuses.append("POSSIBLE_STALE_ROUTE")

    if parsed_distance_km is not None and 70 <= parsed_distance_km <= 95 and not statuses:
        return "OK"

    return "|".join(statuses) if statuses else "OUT_OF_EXPECTED_RANGE"


def classify_attempts(attempts: list[dict[str, Any]]) -> str:
    distances = [item.get("parsed_distance_km") for item in attempts]
    numeric = [value for value in distances if isinstance(value, (int, float))]
    statuses = [str(item.get("status_check") or "") for item in attempts]
    raw_texts = [str(item.get("route_panel_raw_text") or "") for item in attempts]

    if any("ROUTE_NOT_READY" in status for status in statuses):
        return "b) Google Maps load chưa xong"

    if len(numeric) == 3 and all(79 <= value <= 85 for value in numeric):
        return "f) lỗi cũ nhiều khả năng do stale route, selector cũ, mạng/VPN/load chưa ổn định"

    if any(value and 145 <= value <= 153 for value in numeric) and any(79 <= value <= 85 for value in numeric):
        return "f) ảnh hưởng mạng/VPN hoặc kết quả không ổn định, cần retry và lấy median"

    if any("149 km" in text for text in raw_texts):
        return "e) Google Maps/DOM đang trả route có 149 km tại thời điểm test; cần kiểm tra route option/avoid/toll/snap point"

    if any("PARSE_FAILED" in status for status in statuses):
        return "d) parse sai hoặc raw text không đúng định dạng mong đợi"

    if any("SUSPECT_DISTANCE" in status for status in statuses):
        return "c) selector có thể lấy nhầm route/vùng DOM, cần đối chiếu screenshot"

    return "Chưa đủ bằng chứng để kết luận; xem JSON/CSV và screenshot từng attempt"


def run_attempt(
    driver: webdriver.Chrome,
    attempt_number: int,
    url: str,
    origin_input: str,
    destination_input: str,
    previous_raw_text: str | None,
) -> dict[str, Any]:
    crawl_timestamp = datetime.now().isoformat(timespec="seconds")
    driver.get(url)

    try:
        route_panel_raw_text, candidates = wait_for_route_ready(driver)
    except Exception:
        route_panel_raw_text = get_first_text(driver, ROUTE_PANEL_SELECTORS)
        candidates = get_route_candidates(driver)

    selected_route_index = candidates[0]["index"] if candidates else None
    selected_route_raw_text = candidates[0]["text"] if candidates else ""
    parsed_distance_text, parsed_distance_km, all_distance_texts = parse_distance(selected_route_raw_text)
    parsed_duration_text = parse_duration(selected_route_raw_text)
    ratio = (
        round(parsed_distance_km / AIR_DISTANCE_KM, 4)
        if parsed_distance_km is not None and AIR_DISTANCE_KM
        else None
    )
    status_check = build_status(
        route_panel_raw_text=route_panel_raw_text,
        selected_route_raw_text=selected_route_raw_text,
        parsed_distance_km=parsed_distance_km,
        previous_raw_text=previous_raw_text,
    )

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_file = SCREENSHOT_DIR / f"debug_single_route_attempt_{attempt_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    driver.save_screenshot(str(screenshot_file))

    result = {
        "attempt": f"attempt_{attempt_number}",
        "origin_input": origin_input,
        "destination_input": destination_input,
        "google_maps_url": url,
        "crawl_timestamp": crawl_timestamp,
        "current_url_after_load": driver.current_url,
        "page_title": driver.title,
        "route_panel_raw_text": route_panel_raw_text,
        "selected_route_index": selected_route_index,
        "selected_route_raw_text": selected_route_raw_text,
        "parsed_distance_text": parsed_distance_text,
        "parsed_duration_text": parsed_duration_text,
        "parsed_distance_km": parsed_distance_km,
        "khoang_cach_chim_bay": AIR_DISTANCE_KM,
        "ratio_distance_to_air": ratio,
        "status_check": status_check,
        "screenshot_path": str(screenshot_file.relative_to(config.PROJECT_ROOT)),
        "all_distance_texts": all_distance_texts,
    }
    return result


def write_outputs(attempts: list[dict[str, Any]]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"debug_single_route_{timestamp}.json"
    csv_path = OUTPUT_DIR / f"debug_single_route_{timestamp}.csv"

    payload = {
        "summary": {
            "google_maps_url": attempts[0]["google_maps_url"] if attempts else None,
            "conclusion": classify_attempts(attempts),
        },
        "attempts": attempts,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "attempt",
        "origin_input",
        "destination_input",
        "google_maps_url",
        "crawl_timestamp",
        "current_url_after_load",
        "page_title",
        "route_panel_raw_text",
        "selected_route_index",
        "selected_route_raw_text",
        "parsed_distance_text",
        "parsed_duration_text",
        "parsed_distance_km",
        "khoang_cach_chim_bay",
        "ratio_distance_to_air",
        "status_check",
        "screenshot_path",
        "all_distance_texts",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(attempts)

    return json_path, csv_path


def print_attempt(result: dict[str, Any]) -> None:
    print(f"\n{result['attempt']}")
    print(f"  origin_input={result['origin_input']}")
    print(f"  destination_input={result['destination_input']}")
    print(f"  current_url_after_load={result['current_url_after_load']}")
    print(f"  page_title={result['page_title']}")
    print(f"  parsed_distance_text={result['parsed_distance_text']}")
    print(f"  parsed_duration_text={result['parsed_duration_text']}")
    print(f"  parsed_distance_km={result['parsed_distance_km']}")
    print(f"  ratio_distance_to_air={result['ratio_distance_to_air']}")
    print(f"  status_check={result['status_check']}")
    print(f"  screenshot_path={result['screenshot_path']}")
    print(f"  raw_text_distances={result['all_distance_texts']}")


def main() -> None:
    origin_input = f"{ORIGIN_LAT},{ORIGIN_LON}"
    destination_input = f"{DESTINATION_LAT},{DESTINATION_LON}"
    url = build_url(origin_input, destination_input)

    print("Debug single Google Maps route")
    print(f"origin_input={origin_input}")
    print(f"destination_input={destination_input}")
    print(f"google_maps_url={url}")

    attempts: list[dict[str, Any]] = []
    driver = setup_driver()
    try:
        previous_raw_text: str | None = None
        for attempt_number in range(1, ATTEMPTS + 1):
            result = run_attempt(
                driver=driver,
                attempt_number=attempt_number,
                url=url,
                origin_input=origin_input,
                destination_input=destination_input,
                previous_raw_text=previous_raw_text,
            )
            attempts.append(result)
            previous_raw_text = result["selected_route_raw_text"]
            print_attempt(result)
    finally:
        driver.quit()

    json_path, csv_path = write_outputs(attempts)
    conclusion = classify_attempts(attempts)

    print("\nFinal report")
    print(f"  Google Maps URL: {url}")
    print(f"  JSON: {json_path.relative_to(config.PROJECT_ROOT)}")
    print(f"  CSV: {csv_path.relative_to(config.PROJECT_ROOT)}")
    print(f"  Conclusion: {conclusion}")


if __name__ == "__main__":
    main()
