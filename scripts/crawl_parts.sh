#!/usr/bin/env bash
# Chay crawl_part.py cho danh sach PART_ID truyen vao.
#
# Vi du:
#   ./crawl_parts.sh 1 2 3
#   SLEEP_TIME=10 REST_BETWEEN_PARTS=60 ./crawl_parts.sh 901 902 903

set -euo pipefail

cd "$(dirname "$0")"

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 PART_ID [PART_ID ...]"
  exit 1
fi

PYTHON_BIN=${PYTHON_BIN:-python}
REST_BETWEEN_PARTS=${REST_BETWEEN_PARTS:-15}
SLEEP_TIME=${SLEEP_TIME:-3}
WAIT_TIME=${WAIT_TIME:-10}
BATCH_SIZE=${BATCH_SIZE:-100}

LAST_INDEX=$(($# - 1))
idx=0

for part in "$@"; do
  echo ""
  echo "========== Part $part | $(date '+%Y-%m-%d %H:%M:%S') =========="
  PART_ID=$part SLEEP_TIME=$SLEEP_TIME WAIT_TIME=$WAIT_TIME BATCH_SIZE=$BATCH_SIZE "$PYTHON_BIN" crawl_part.py
  echo "========== Xong part $part =========="

  if [ "$idx" -lt "$LAST_INDEX" ]; then
    echo "Nghi ${REST_BETWEEN_PARTS}s truoc part tiep theo..."
    sleep "$REST_BETWEEN_PARTS"
  fi

  idx=$((idx + 1))
done

echo ""
echo "Da chay xong danh sach part."
