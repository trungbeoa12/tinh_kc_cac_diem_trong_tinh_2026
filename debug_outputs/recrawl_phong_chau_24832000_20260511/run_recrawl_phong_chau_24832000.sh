#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

mkdir -p "debug_outputs/recrawl_phong_chau_24832000_20260511/output"

python scripts/recrawl_high_priority.py \
  --input-file "debug_outputs/recrawl_phong_chau_24832000_20260511/recrawl_phong_chau_24832000_updated_coords.csv" \
  --output-dir "debug_outputs/recrawl_phong_chau_24832000_20260511/output" \
  --machine-id "PHONG_CHAU_24832000" \
  --overwrite
