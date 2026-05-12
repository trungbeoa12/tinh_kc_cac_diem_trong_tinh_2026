#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/trungdt2/Documents/crawl_all_khoang_cach/tinh_kc_cac_diem_trong_tinh_2026"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
INPUT_FILE="outputs/compare_distance_3_periods/recrawl_batch_01.csv"
OUTPUT_DIR="outputs/compare_distance_3_periods/recrawl_outputs/batch_01"
LOG_DIR="outputs/compare_distance_3_periods/recrawl_outputs/logs"
SLEEP_TIME="${SLEEP_TIME:-2}"
WAIT_TIME="${WAIT_TIME:-30}"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

echo "========== Recrawl batch 01 | $(date '+%Y-%m-%d %H:%M:%S') =========="
echo "Project root: $PROJECT_ROOT"
echo "Input file: $INPUT_FILE"
echo "Output dir: $OUTPUT_DIR"
echo "SLEEP_TIME=$SLEEP_TIME WAIT_TIME=$WAIT_TIME"

"$PYTHON_BIN" scripts/recrawl_high_priority.py \
  --input-file "$INPUT_FILE" \
  --output-dir "$OUTPUT_DIR" \
  --machine-id "BATCH_01" \
  --sleep-time "$SLEEP_TIME" \
  --wait-time "$WAIT_TIME" \
  2>&1 | tee "$LOG_DIR/recrawl_batch_01.log"

echo "========== Done recrawl batch 01 | $(date '+%Y-%m-%d %H:%M:%S') =========="
