#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

mkdir -p "debug_outputs/recrawl_all_suspects_20260504_vs_20260312/logs"
mkdir -p "debug_outputs/recrawl_all_suspects_20260504_vs_20260312/output_batch_02"

echo "Start time: $(date)"
echo "Input file: debug_outputs/recrawl_all_suspects_20260504_vs_20260312/recrawl_batch_02.csv"
echo "Output dir: debug_outputs/recrawl_all_suspects_20260504_vs_20260312/output_batch_02"

python scripts/recrawl_high_priority.py \
  --input-file "debug_outputs/recrawl_all_suspects_20260504_vs_20260312/recrawl_batch_02.csv" \
  --output-dir "debug_outputs/recrawl_all_suspects_20260504_vs_20260312/output_batch_02" \
  --machine-id "BATCH_02" \
  2>&1 | tee "debug_outputs/recrawl_all_suspects_20260504_vs_20260312/logs/recrawl_batch_02.log"

echo "End time: $(date)"
