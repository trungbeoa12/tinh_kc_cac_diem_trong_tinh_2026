#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

bash run_recrawl_batch_01.sh
bash run_recrawl_batch_02.sh
bash run_recrawl_batch_03.sh

# Nếu muốn chạy song song, có thể tự chạy 3 lệnh dưới đây ở 3 terminal riêng:
# bash run_recrawl_batch_01.sh
# bash run_recrawl_batch_02.sh
# bash run_recrawl_batch_03.sh
