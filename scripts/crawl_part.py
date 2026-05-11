#!/usr/bin/env python
# coding: utf-8

from __future__ import annotations

import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Import config
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# ========== LOGGING SETUP ==========
def setup_logging(part_id: int) -> logging.Logger:
    """Setup logging with both console and file output."""
    log_dir = config.PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"crawl_part_{part_id:02d}_{timestamp}.log"
    
    logger = logging.getLogger(f"crawl_part_{part_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    
    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter(config.LOG_FORMAT, datefmt=config.LOG_DATE_FORMAT)
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


# ========== CẤU HÌNH ==========
PART_ID = int(os.environ.get("PART_ID", "1"))
DATA_FOLDER = Path(os.environ.get("PART_FOLDER", config.PART_FOLDER))
OUTPUT_FOLDER = DATA_FOLDER / f"output_part_{PART_ID:02d}"
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
SCREENSHOT_FOLDER = config.PROJECT_ROOT / "debug_screenshots"

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", config.CRAWL_DEFAULTS["BATCH_SIZE"]))
SLEEP_TIME = float(os.environ.get("SLEEP_TIME", config.CRAWL_DEFAULTS["SLEEP_TIME"]))
WAIT_TIME = int(os.environ.get("WAIT_TIME", config.CRAWL_DEFAULTS["WAIT_TIME"]))
MAX_ROWS = os.environ.get("MAX_ROWS")

logger = setup_logging(PART_ID)

DEBUG_COLUMNS = config.DEBUG_COLUMNS

ROUTE_PANEL_SELECTORS = [
    "div[role='main']",
    "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
    "div.section-directions-trip",
    "body",
]

DISTANCE_ANYWHERE_RE = re.compile(r"(?P<num>\d+(?:[,.]\d+)?)\s*(?P<unit>km|m)\b", re.I)
DURATION_ANYWHERE_RE = re.compile(
    r"(?:(?:\d+\s*(?:hr|hour|hours|h|giờ|gio))\s*)?\d+\s*(?:min|mins|minute|minutes|phút|phut)\b|"
    r"\d+\s*(?:hr|hour|hours|h|giờ|gio)\b",
    re.I,
)


def _clean_text(value: str | None) -> str:
    return " ".join(str(value or "").split())


def parse_distance_text(value: str | None) -> tuple[str | None, float | None]:
    text = str(value or "")
    matches = list(DISTANCE_ANYWHERE_RE.finditer(text))
    if not matches:
        return None, None

    # In route cards the usable distance is normally the last distance-like token.
    match = matches[-1]
    distance_text = match.group(0)
    number = float(match.group("num").replace(",", "."))
    unit = match.group("unit").lower()
    km = number if unit == "km" else number / 1000
    return distance_text, round(km, 2)


def parse_duration_text(value: str | None) -> str | None:
    match = DURATION_ANYWHERE_RE.search(str(value or ""))
    return match.group(0) if match else None


def build_status_check(
    route_panel_raw_text: str,
    selected_route_raw_text: str,
    parsed_distance_km: float | None,
    air_distance_km: float | None,
    previous_route_raw_text: str | None,
) -> str:
    statuses: list[str] = []
    panel_text = route_panel_raw_text or ""

    if parsed_distance_km is None:
        statuses.append("PARSE_FAILED")

    has_distance = bool(DISTANCE_ANYWHERE_RE.search(panel_text))
    has_duration = bool(DURATION_ANYWHERE_RE.search(panel_text))
    if not has_distance or not has_duration:
        statuses.append("ROUTE_NOT_READY")

    if (
        parsed_distance_km is not None
        and air_distance_km is not None
        and air_distance_km > 0
        and parsed_distance_km / air_distance_km > 1.8
    ):
        statuses.append("SUSPECT_DISTANCE")

    if (
        previous_route_raw_text
        and selected_route_raw_text
        and _clean_text(previous_route_raw_text) == _clean_text(selected_route_raw_text)
    ):
        statuses.append("POSSIBLE_STALE_ROUTE")

    return "|".join(statuses) if statuses else "OK"

# ========== TRÌNH DUYỆT ==========
class GoogleMapsDistanceCalculator:
    def __init__(self, logger: logging.Logger):
        self.driver = None
        self.logger = logger
        self.consecutive_not_found = 0
        self.previous_route_raw_text: str | None = None
        self.setup_driver()

    def setup_driver(self):
        """Initialize Chrome webdriver with headless options."""
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.logger.debug("✓ Chrome webdriver initialized")
        except Exception as e:
            self.logger.error(f"✗ Failed to initialize webdriver: {e}")
            raise

    def _get_first_text(self, selectors: list[str]) -> str:
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text:
                        return text
            except Exception:
                continue
        return ""

    def _wait_for_route_panel_text(self) -> str:
        def panel_has_route_text(driver):
            text = self._get_first_text(ROUTE_PANEL_SELECTORS)
            if DISTANCE_ANYWHERE_RE.search(text) or config.ERROR_KEYWORDS.search(text):
                return text
            return False

        try:
            return WebDriverWait(self.driver, WAIT_TIME).until(panel_has_route_text)
        except Exception:
            return self._get_first_text(ROUTE_PANEL_SELECTORS)

    def _capture_screenshot(self, row_key: str) -> str:
        SCREENSHOT_FOLDER.mkdir(parents=True, exist_ok=True)
        filename = f"part_{PART_ID:02d}_{row_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = SCREENSHOT_FOLDER / filename
        self.driver.save_screenshot(str(path))
        try:
            return str(path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            return str(path)

    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        air_distance_km: float | None = None,
        row_key: str = "row",
    ) -> tuple[str | None, dict[str, object]]:
        """
        Query Google Maps for distance between two coordinates.
        
        Returns:
            Tuple of distance text and debug metadata.
        """
        origin_input = f"{lat1},{lon1}"
        destination_input = f"{lat2},{lon2}"
        url = f"https://www.google.com/maps/dir/{origin_input}/{destination_input}/data=!4m2!4m1!3e0"
        debug_info: dict[str, object] = {
            "origin_input": origin_input,
            "destination_input": destination_input,
            "google_maps_url": url,
            "crawl_timestamp": datetime.now().isoformat(timespec="seconds"),
            "route_panel_raw_text": "",
            "selected_route_index": None,
            "selected_route_raw_text": "",
            "parsed_distance_text": None,
            "parsed_duration_text": None,
            "parsed_distance_km": None,
            "screenshot_path": None,
            "status_check": "ERROR",
        }

        try:
            self.driver.get(url)
            time.sleep(2)
            route_panel_raw_text = self._wait_for_route_panel_text()
            debug_info["route_panel_raw_text"] = route_panel_raw_text
            
            result = None
            selected_route_index = None
            # Try multiple selectors
            for selector in config.GOOGLE_MAPS_SELECTORS:
                try:
                    elements = WebDriverWait(self.driver, WAIT_TIME).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    for element_index, element in enumerate(elements):
                        text = element.text.strip()
                        if not text:
                            continue
                        result = text
                        selected_route_index = element_index
                        break
                    if result:
                        break
                except Exception:
                    continue
            
            if result is None:
                result = "Không tìm thấy"

            parsed_distance_text, parsed_distance_km = parse_distance_text(result)
            parsed_duration_text = parse_duration_text(result)
            debug_info.update(
                {
                    "selected_route_index": selected_route_index,
                    "selected_route_raw_text": result,
                    "parsed_distance_text": parsed_distance_text,
                    "parsed_duration_text": parsed_duration_text,
                    "parsed_distance_km": parsed_distance_km,
                    "status_check": build_status_check(
                        route_panel_raw_text=route_panel_raw_text,
                        selected_route_raw_text=result,
                        parsed_distance_km=parsed_distance_km,
                        air_distance_km=air_distance_km,
                        previous_route_raw_text=self.previous_route_raw_text,
                    ),
                }
            )

            if "SUSPECT_DISTANCE" in str(debug_info["status_check"]):
                debug_info["screenshot_path"] = self._capture_screenshot(row_key)
            
            # Check for rate-limit indicators
            if config.ERROR_KEYWORDS.search(result):
                self.consecutive_not_found += 1
                self.logger.debug(f"Not found or error detected (consecutive: {self.consecutive_not_found})")
            else:
                self.consecutive_not_found = 0

            self.previous_route_raw_text = result
            
            return result, debug_info
            
        except Exception as e:
            self.logger.warning(f"Error during crawl: {e}")
            debug_info["status_check"] = "ERROR"
            return None, debug_info

    def check_rate_limit(self, failed_count: int, batch_size: int) -> bool:
        """
        Detect if Google Maps is rate-limiting us.
        
        Returns True if rate-limit is likely detected.
        """
        consecutive_threshold = config.RATE_LIMIT_THRESHOLDS["consecutive_not_found"]
        not_found_pct_threshold = config.RATE_LIMIT_THRESHOLDS["not_found_percentage"]
        
        # Check consecutive "not found" errors
        if self.consecutive_not_found >= consecutive_threshold:
            self.logger.warning(
                f"⚠️  Rate-limit detected: {self.consecutive_not_found} consecutive not found errors"
            )
            return True
        
        # Check percentage of failed rows in batch
        if batch_size > 0 and failed_count / batch_size >= not_found_pct_threshold:
            self.logger.warning(
                f"⚠️  Rate-limit detected: {failed_count}/{batch_size} ({failed_count/batch_size*100:.1f}%) rows failed"
            )
            return True
        
        return False

    def close(self):
        """Close webdriver."""
        if self.driver:
            self.driver.quit()
            self.logger.debug("Chrome webdriver closed")

# ========== CHẠY CRAWL ==========
def crawl_with_resume(df_input: pd.DataFrame) -> None:
    """
    Crawl Google Maps with resume capability and rate-limit detection.
    """
    df = df_input.copy().reset_index(drop=True)
    total_rows = len(df)
    total_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE

    if config.DISTANCE_COL not in df.columns:
        df[config.DISTANCE_COL] = None
    else:
        # Ensure this column can safely hold text values from Google Maps.
        df[config.DISTANCE_COL] = df[config.DISTANCE_COL].astype("object")

    for column in DEBUG_COLUMNS:
        if column not in df.columns:
            df[column] = None
        df[column] = df[column].astype("object")

    logger.info(f"Starting crawl: {total_rows} rows, {total_batches} batches")
    logger.info(f"Configuration: BATCH_SIZE={BATCH_SIZE}, SLEEP_TIME={SLEEP_TIME}s, WAIT_TIME={WAIT_TIME}s")

    for batch_idx in range(total_batches):
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min((batch_idx + 1) * BATCH_SIZE, total_rows)
        output_file = OUTPUT_FOLDER / f"ket_qua_tu_{start_idx}_den_{end_idx - 1}.xlsx"

        if output_file.exists():
            logger.info(f"⏭️  Skipping batch {batch_idx+1}/{total_batches} ({start_idx}-{end_idx-1}) - already exists")
            continue

        logger.info(f"🚀 Starting batch {batch_idx+1}/{total_batches} ({start_idx}-{end_idx-1})...")
        calculator = GoogleMapsDistanceCalculator(logger)
        batch_failed_count = 0

        try:
            for idx in range(start_idx, end_idx):
                if pd.notna(df.at[idx, config.DISTANCE_COL]):
                    continue

                row = df.loc[idx]
                lat1, lon1 = row['vi_do_1'], row['kinh_do_1']
                lat2, lon2 = row['vi_do_2'], row['kinh_do_2']
                air_distance_km = row.get("khoang_cach_chim_bay")
                if pd.isna(air_distance_km):
                    air_distance_km = None

                logger.debug(f"Row {idx}: ({lat1},{lon1}) → ({lat2},{lon2})")
                distance, debug_info = calculator.calculate_distance(
                    lat1=lat1,
                    lon1=lon1,
                    lat2=lat2,
                    lon2=lon2,
                    air_distance_km=float(air_distance_km) if air_distance_km is not None else None,
                    row_key=f"row_{idx}",
                )

                for column, value in debug_info.items():
                    df.at[idx, column] = value
                
                if distance is None:
                    batch_failed_count += 1
                    logger.warning(f"  ✗ Error getting result")
                else:
                    df.at[idx, config.DISTANCE_COL] = distance
                    if "Không tìm thấy" in str(distance):
                        batch_failed_count += 1
                        logger.debug(f"  → Not found")
                    else:
                        logger.debug(f"  → {distance[:50]}")

                if str(debug_info.get("status_check")) != "OK":
                    logger.warning(
                        "  Debug status %s | origin=%s | destination=%s | parsed=%s | screenshot=%s",
                        debug_info.get("status_check"),
                        debug_info.get("origin_input"),
                        debug_info.get("destination_input"),
                        debug_info.get("parsed_distance_km"),
                        debug_info.get("screenshot_path"),
                    )
                
                time.sleep(SLEEP_TIME)
                
                # Check for rate-limit every row
                if calculator.check_rate_limit(batch_failed_count, idx - start_idx + 1):
                    logger.warning(
                        f"⚠️  RATE-LIMIT LIKELY DETECTED in batch {batch_idx+1}."
                        f"\n    Please stop and retry later with slower settings:"
                        f"\n    SLEEP_TIME=5 WAIT_TIME=15 REST_BETWEEN_PARTS=120"
                    )
                    # Don't break - let user decide when to stop via Ctrl+C

        finally:
            calculator.close()
        
        # Save batch
        df.iloc[start_idx:end_idx].to_excel(output_file, index=False)
        logger.info(f"✓ Saved batch to: {output_file}")
        logger.info(f"  Summary: {batch_failed_count} rows failed/not found out of {end_idx - start_idx}")

    logger.info("✓ Completed all batches")


# ========== CHẠY ==========
def main():
    try:
        file_path = DATA_FOLDER / f"df_part_{PART_ID:02d}.pkl"
        logger.info(f"Loading data from: {file_path}")
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            sys.exit(1)
        
        df_part = pd.read_pickle(file_path)
        
        if MAX_ROWS:
            df_part = df_part.head(int(MAX_ROWS))
            logger.info(f"Limited to {len(df_part)} rows (MAX_ROWS={MAX_ROWS})")
        
        crawl_with_resume(df_part)
        logger.info(f"✓ Part {PART_ID} completed successfully")
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
