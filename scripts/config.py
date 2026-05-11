"""Centralized configuration for crawl project."""

from pathlib import Path

# ===== PROJECT PATHS =====
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Data version (format: YYYYMMDD)
DATA_VERSION = "20260504"

# ===== INPUT/OUTPUT PATHS =====
# Adjust DATA_VERSION when running for new data
def get_data_paths(version: str = DATA_VERSION):
    """Get data paths for given version."""
    data_folder = PROJECT_ROOT / f"data_{version}"
    return {
        "input_folder": data_folder / "input",
        "final_folder": data_folder / "final",
        "diagnostics_folder": data_folder / "diagnostics",
        "branches_file": data_folder / f"input/branches_{version}.xlsx",
        "crawl_pairs_file": data_folder / f"input/crawl_pairs_{version}.xlsx",
        "final_file": data_folder / f"final/road_distance_{version}_final.xlsx",
        "failed_file": data_folder / f"diagnostics/failed_rows_{version}.xlsx",
        "summary_file": data_folder / f"diagnostics/finalize_summary_{version}.txt",
    }


# ===== COLUMN NAMES (Vietnamese) =====
COLUMN_MAP = {
    "Mã phòng ban": "ma_phong_ban",
    "Tên phòng ban": "ten_phong_ban",
    "KINH ĐỘ": "kinh_do",
    "VĨ ĐỘ": "vi_do",
    "Tỉnh": "tinh_thanh",
}

DISTANCE_COL = "Khoảng cách đường bộ"
KM_COL = "Khoảng cách đường bộ km"
TIME_COL = "thời gian"
STATUS_COL = "crawl_status"

DEBUG_COLUMNS = [
    "origin_input",
    "destination_input",
    "google_maps_url",
    "crawl_timestamp",
    "route_panel_raw_text",
    "selected_route_index",
    "selected_route_raw_text",
    "parsed_distance_text",
    "parsed_duration_text",
    "parsed_distance_km",
    "screenshot_path",
    "status_check",
]

# ===== CRAWL CONFIGURATION =====
# Default environment variables from crawl_parts.sh
CRAWL_DEFAULTS = {
    "BATCH_SIZE": 100,
    "SLEEP_TIME": 2,  # seconds between rows
    "WAIT_TIME": 10,  # seconds to wait for Google Maps to render
    "REST_BETWEEN_PARTS": 15,  # seconds between parts
}

# Rate-limit detection thresholds
RATE_LIMIT_THRESHOLDS = {
    "consecutive_not_found": 10,  # If >10 consecutive "not found", likely rate-limited
    "not_found_percentage": 0.5,  # If >50% not found in batch, likely rate-limited
}

# ===== GOOGLE MAPS SELECTORS =====
GOOGLE_MAPS_SELECTORS = [
    "div.xB1mrd-T3iPGc-iSfDt-ij8cu",  # Distance element (newer version)
    "div.XdKEzd",  # Alternative selector
]

# ===== REGEX PATTERNS =====
import re

# Parse distance from Google Maps (e.g., "33.8 km", "900 m")
DISTANCE_REGEX = re.compile(
    r"(?P<num>\d+(?:[,.]\d+)?)\s*(?P<unit>km|m)\s*$", re.I
)

# Detect error states in Google Maps response
ERROR_KEYWORDS = re.compile(
    r"Không tìm thấy|Khong tim thay|not found|error|lỗi|loi", re.I
)

# ===== LOGGING =====
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ===== CRAWL WORK FOLDER =====
WORK_FOLDER = PROJECT_ROOT / "work"
PART_FOLDER = WORK_FOLDER / "part"
