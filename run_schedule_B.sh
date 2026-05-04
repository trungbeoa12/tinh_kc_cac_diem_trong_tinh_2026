#!/usr/bin/env bash
# Terminal B: chạy run_crawl_part_B.py lần lượt các part lẻ từ 13 → 55
# Đã chạy xong part 1–11, bắt đầu từ part 13.

cd "$(dirname "$0")"

for part in 13 15 17 19 21 23 25 27 29 31 33 35 37 39 41 43 45 47 49 51 53 55; do
  echo ""
  echo "========== Terminal B: Part $part =========="
  PART_ID=$part python run_crawl_part_B.py
  echo "========== Xong part $part =========="
done

echo ""
echo "🎉 Terminal B: Đã chạy xong tất cả part lẻ 13–55."
