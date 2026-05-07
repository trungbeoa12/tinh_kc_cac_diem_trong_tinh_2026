#!/usr/bin/env python
# coding: utf-8

from __future__ import annotations

import logging
import os
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

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", config.CRAWL_DEFAULTS["BATCH_SIZE"]))
SLEEP_TIME = float(os.environ.get("SLEEP_TIME", config.CRAWL_DEFAULTS["SLEEP_TIME"]))
WAIT_TIME = int(os.environ.get("WAIT_TIME", config.CRAWL_DEFAULTS["WAIT_TIME"]))
MAX_ROWS = os.environ.get("MAX_ROWS")

logger = setup_logging(PART_ID)

# ========== TRÌNH DUYỆT ==========
class GoogleMapsDistanceCalculator:
    def __init__(self, logger: logging.Logger):
        self.driver = None
        self.logger = logger
        self.consecutive_not_found = 0
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

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> str | None:
        """
        Query Google Maps for distance between two coordinates.
        
        Returns:
            Distance text from Google Maps, "Không tìm thấy" if not found, or None on error.
        """
        try:
            url = f"https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}/data=!4m2!4m1!3e0"
            self.driver.get(url)
            time.sleep(4)
            
            result = None
            # Try multiple selectors
            for selector in config.GOOGLE_MAPS_SELECTORS:
                try:
                    element = WebDriverWait(self.driver, WAIT_TIME).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    result = element.text
                    break
                except:
                    continue
            
            if result is None:
                result = "Không tìm thấy"
            
            # Check for rate-limit indicators
            if config.ERROR_KEYWORDS.search(result):
                self.consecutive_not_found += 1
                self.logger.debug(f"Not found or error detected (consecutive: {self.consecutive_not_found})")
            else:
                self.consecutive_not_found = 0
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Error during crawl: {e}")
            return None

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

                logger.debug(f"Row {idx}: ({lat1},{lon1}) → ({lat2},{lon2})")
                distance = calculator.calculate_distance(lat1, lon1, lat2, lon2)
                
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
