#!/usr/bin/env bash
# Terminal missing 1: chay cac part con thieu 149, 242-257.

set -euo pipefail

cd "$(dirname "$0")"

REST_BETWEEN_PARTS=${REST_BETWEEN_PARTS:-15}
SLEEP_TIME=${SLEEP_TIME:-3}
WAIT_TIME=${WAIT_TIME:-10}
BATCH_SIZE=${BATCH_SIZE:-100}

PARTS=(149 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257)
LAST_PART=${PARTS[$((${#PARTS[@]} - 1))]}

for part in "${PARTS[@]}"; do
  echo ""
  echo "========== Missing 1: Part $part | $(date '+%Y-%m-%d %H:%M:%S') =========="
  PART_ID=$part SLEEP_TIME=$SLEEP_TIME WAIT_TIME=$WAIT_TIME BATCH_SIZE=$BATCH_SIZE python run_crawl_part.py
  echo "========== Xong part $part =========="

  if [ "$part" -ne "$LAST_PART" ]; then
    echo "Nghi ${REST_BETWEEN_PARTS}s truoc part tiep theo..."
    sleep "$REST_BETWEEN_PARTS"
  fi
done

echo ""
echo "Missing 1: Da chay xong cac part duoc giao."
