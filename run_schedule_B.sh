#!/usr/bin/env bash
# Terminal B: chay run_crawl_part.py cho cac part chan cua data_20260504.

set -euo pipefail

cd "$(dirname "$0")"

REST_BETWEEN_PARTS=${REST_BETWEEN_PARTS:-300}
SLEEP_TIME=${SLEEP_TIME:-3}
WAIT_TIME=${WAIT_TIME:-10}
BATCH_SIZE=${BATCH_SIZE:-100}

for part in $(seq 2 2 308); do
  echo ""
  echo "========== Terminal B: Part $part | $(date '+%Y-%m-%d %H:%M:%S') =========="
  PART_ID=$part SLEEP_TIME=$SLEEP_TIME WAIT_TIME=$WAIT_TIME BATCH_SIZE=$BATCH_SIZE python run_crawl_part.py
  echo "========== Xong part $part =========="

  if [ "$part" -lt 308 ]; then
    echo "Nghi ${REST_BETWEEN_PARTS}s truoc part tiep theo..."
    sleep "$REST_BETWEEN_PARTS"
  fi
done

echo ""
echo "Terminal B: Da chay xong cac part chan."
