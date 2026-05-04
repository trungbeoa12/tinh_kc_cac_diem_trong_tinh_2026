#!/usr/bin/env bash
# Terminal A: chạy run_crawl_part.py lần lượt các part chẵn từ 12 → 56
# Đã chạy xong part 1–11, bắt đầu từ part 12.

cd "$(dirname "$0")"

for part in 12 14 16 18 20 22 24 26 28 30 32 34 36 38 40 42 44 46 48 50 52 54 56; do
  echo ""
  echo "========== Terminal A: Part $part =========="
  PART_ID=$part python run_crawl_part.py
  echo "========== Xong part $part =========="
done

echo ""
echo "🎉 Terminal A: Đã chạy xong tất cả part chẵn 12–56."
